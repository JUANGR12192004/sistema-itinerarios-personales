"""Pruebas del proceso del Outbox Relay (app/outbox_relay.py), sin PostgreSQL ni RabbitMQ."""

import logging

import pytest

from app.application.outbox_relay import OutboxRelay, RelayResult
from app.config import Settings
from app.outbox_relay import build_relay, run_cycle, run_loop

DATABASE_URL = "postgresql+psycopg://localhost:5433/itinerary_db"


class FakeSession:
    """Sesión mínima para run_cycle: sirve como context manager y cuenta los rollbacks."""

    def __init__(self) -> None:
        self.rollbacks = 0

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def rollback(self) -> None:
        self.rollbacks += 1


def _settings() -> Settings:
    return Settings(_env_file=None, database_url=DATABASE_URL, outbox_relay_batch_size=3)


def test_build_relay_ensambla_un_outbox_relay():
    relay = build_relay(FakeSession(), _settings())  # type: ignore[arg-type]

    assert isinstance(relay, OutboxRelay)


def test_run_cycle_hace_rollback_si_el_ciclo_falla(monkeypatch: pytest.MonkeyPatch):
    session = FakeSession()

    class FailingRelay:
        def run_once(self) -> RelayResult:
            raise RuntimeError("fallo simulado")

    monkeypatch.setattr("app.outbox_relay.build_relay", lambda s, settings: FailingRelay())

    with pytest.raises(RuntimeError):
        run_cycle(lambda: session, _settings())  # type: ignore[arg-type]

    assert session.rollbacks == 1


def test_espera_el_intervalo_entre_ciclos():
    sleeps: list[float] = []

    run_loop(lambda: RelayResult(), interval_seconds=2.0, batch_size=10, sleep=sleeps.append, max_cycles=3)

    assert sleeps == [2.0, 2.0, 2.0]


def test_no_espera_si_publico_un_lote_completo():
    """Con un lote completo probablemente quedan más pendientes: sigue sin esperar."""
    results = iter([RelayResult(published=10), RelayResult(published=4)])
    sleeps: list[float] = []

    run_loop(lambda: next(results), interval_seconds=2.0, batch_size=10, sleep=sleeps.append, max_cycles=2)

    assert sleeps == [2.0]  # solo después del segundo ciclo


def test_los_descartados_cuentan_para_el_lote_completo():
    """Un lote de mensajes venenosos descartados también deja pendientes por revisar."""
    results = iter([RelayResult(published=6, dead=4), RelayResult()])
    sleeps: list[float] = []

    run_loop(lambda: next(results), interval_seconds=2.0, batch_size=10, sleep=sleeps.append, max_cycles=2)

    assert sleeps == [2.0]


def test_con_fallos_temporales_siempre_espera():
    """Con RabbitMQ caído no se reintenta sin pausa, aunque el lote sea de 1."""
    sleeps: list[float] = []

    run_loop(lambda: RelayResult(failed=1), interval_seconds=2.0, batch_size=1, sleep=sleeps.append, max_cycles=2)

    assert sleeps == [2.0, 2.0]


def test_un_ciclo_fallido_no_detiene_el_proceso(caplog):
    calls: list[int] = []

    def cycle() -> RelayResult:
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("PostgreSQL no disponible (simulado)")
        return RelayResult(published=1)

    with caplog.at_level(logging.ERROR, logger="app.outbox_relay"):
        run_loop(cycle, interval_seconds=1.0, batch_size=10, sleep=lambda _: None, max_cycles=2)

    assert len(calls) == 2
    assert "Falló un ciclo del Outbox Relay" in caplog.text
