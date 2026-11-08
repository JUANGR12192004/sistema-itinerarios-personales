"""Pruebas de CreateItineraryUseCase centradas en el registro del evento (Fase 5).

Verifican el orden del Transactional Outbox (ADR-026):
guardar → registrar el evento → commit, y que un fallo al registrar el evento
impide el commit (el itinerario no se confirma sin su evento).
"""

import logging
from datetime import datetime, timedelta, timezone

import pytest

from app.application.exceptions import (
    AirportServiceUnavailableError,
    DepartureAirportNotFoundError,
    EventPublishError,
)
from app.application.use_cases import CreateItineraryCommand, CreateItineraryUseCase
from tests.fakes import (
    FakeAirportCatalog,
    FakeEventPublisher,
    FakeItineraryRepository,
    FakeUnitOfWork,
)

FUTURE = datetime.now(timezone.utc) + timedelta(days=30)


def _command(**overrides) -> CreateItineraryCommand:
    values = dict(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=FUTURE,
        duration_minutes=75,
        traveler_email="ana@example.com",
        correlation_id="cid-42",
    )
    values.update(overrides)
    return CreateItineraryCommand(**values)


def _use_case(
    catalog: FakeAirportCatalog | None = None,
    publisher_fails: bool = False,
) -> tuple[CreateItineraryUseCase, FakeItineraryRepository, FakeUnitOfWork, FakeEventPublisher, list[str]]:
    calls: list[str] = []
    repo = FakeItineraryRepository(calls)
    uow = FakeUnitOfWork(calls)
    publisher = FakeEventPublisher(fail=publisher_fails, calls=calls)
    use_case = CreateItineraryUseCase(repo, catalog or FakeAirportCatalog(), uow, publisher)
    return use_case, repo, uow, publisher, calls


def test_registra_el_evento_antes_del_commit():
    """El evento debe entrar en la misma transacción que el itinerario."""
    use_case, _, _, _, calls = _use_case()

    use_case.execute(_command())

    assert calls == ["save", "publish", "commit"]


def test_registra_un_evento_con_los_datos_del_itinerario():
    use_case, _, _, publisher, _ = _use_case()

    itinerary = use_case.execute(_command())

    assert len(publisher.published) == 1
    event = publisher.published[0]
    assert event.itinerary_id == itinerary.id
    assert event.traveler_email == "ana@example.com"
    assert event.correlation_id == "cid-42"


def test_aeropuerto_inexistente_no_hace_commit_ni_registra_evento():
    use_case, repo, uow, publisher, _ = _use_case(catalog=FakeAirportCatalog(existing_ids={5}))

    with pytest.raises(DepartureAirportNotFoundError):
        use_case.execute(_command())

    assert repo.list_all() == []
    assert uow.commits == 0
    assert publisher.published == []


def test_airport_service_caido_no_hace_commit_ni_registra_evento():
    use_case, _, uow, publisher, _ = _use_case(catalog=FakeAirportCatalog(unavailable=True))

    with pytest.raises(AirportServiceUnavailableError):
        use_case.execute(_command())

    assert uow.commits == 0
    assert publisher.published == []


def test_si_falla_el_registro_del_evento_no_hay_commit():
    """Sin evento no hay itinerario: el error se propaga y la transacción no se confirma.

    El rollback real lo hace get_db_session (o el llamador); aquí basta con
    comprobar que el caso de uso nunca llegó a confirmar.
    """
    use_case, _, uow, _, calls = _use_case(publisher_fails=True)

    with pytest.raises(EventPublishError):
        use_case.execute(_command())

    assert uow.commits == 0
    assert calls == ["save", "publish"]


def test_ya_no_registra_evento_perdido(caplog):
    """El log "Evento perdido" de la Fase 4 desaparece: el evento no se puede perder."""
    use_case, _, _, _, _ = _use_case()

    with caplog.at_level(logging.INFO, logger="app.application.use_cases"):
        itinerary = use_case.execute(_command())

    assert "Evento perdido" not in caplog.text
    assert f"Itinerario creado: id={itinerary.id}" in caplog.text
