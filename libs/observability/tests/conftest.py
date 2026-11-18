"""Fixtures comunes de las pruebas de libs/observability.

El paquete guarda estado GLOBAL (el logger "app", el TracerProvider de OpenTelemetry y los
contadores de Prometheus). Estas fixtures lo aíslan para que cada prueba empiece limpia.
"""

import logging
from collections.abc import Iterator

import pytest

from observability import tracing


@pytest.fixture
def app_logger() -> Iterator[logging.Logger]:
    """El logger "app" sin handlers; al terminar se restaura como estaba."""
    logger = logging.getLogger("app")
    saved = (list(logger.handlers), logger.level, logger.propagate)
    logger.handlers.clear()
    yield logger
    logger.handlers[:] = saved[0]
    logger.setLevel(saved[1])
    logger.propagate = saved[2]


class FakeLoggingInstrumentor:
    """Sustituye a LoggingInstrumentor: registra la llamada sin modificar el logging real."""

    calls = 0

    def instrument(self) -> None:
        FakeLoggingInstrumentor.calls += 1


@pytest.fixture
def tracing_state(monkeypatch: pytest.MonkeyPatch) -> list:
    """Reinicia setup_tracing y captura el TracerProvider en lugar de instalarlo globalmente.

    OpenTelemetry solo permite fijar el provider global una vez por proceso; capturarlo deja
    que cada prueba llame a setup_tracing como si fuera el arranque del servicio.
    """
    installed: list = []
    monkeypatch.setattr(tracing, "_initialized", False)
    monkeypatch.setattr(tracing.trace, "set_tracer_provider", installed.append)
    monkeypatch.setattr(tracing, "LoggingInstrumentor", FakeLoggingInstrumentor)
    monkeypatch.delenv("OTEL_ENABLED", raising=False)
    FakeLoggingInstrumentor.calls = 0
    return installed
