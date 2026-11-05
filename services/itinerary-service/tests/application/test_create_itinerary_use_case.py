"""Pruebas de CreateItineraryUseCase centradas en la publicación del evento (Fase 4).

Verifican la "publicación directa tras el commit" (ADR-022):
guardar → commit → publicar, y qué pasa cuando la publicación falla.
"""

import logging
from datetime import datetime, timedelta, timezone

import pytest

from app.application.exceptions import (
    AirportServiceUnavailableError,
    DepartureAirportNotFoundError,
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
    repo = FakeItineraryRepository()
    uow = FakeUnitOfWork(calls)
    publisher = FakeEventPublisher(fail=publisher_fails, calls=calls)
    use_case = CreateItineraryUseCase(repo, catalog or FakeAirportCatalog(), uow, publisher)
    return use_case, repo, uow, publisher, calls


def test_publica_despues_del_commit():
    use_case, _, _, _, calls = _use_case()

    use_case.execute(_command())

    assert calls == ["commit", "publish"]


def test_publica_un_evento_con_los_datos_del_itinerario():
    use_case, _, _, publisher, _ = _use_case()

    itinerary = use_case.execute(_command())

    assert len(publisher.published) == 1
    event = publisher.published[0]
    assert event.itinerary_id == itinerary.id
    assert event.traveler_email == "ana@example.com"
    assert event.correlation_id == "cid-42"


def test_aeropuerto_inexistente_no_hace_commit_ni_publica():
    use_case, repo, uow, publisher, _ = _use_case(catalog=FakeAirportCatalog(existing_ids={5}))
    command = _command()

    with pytest.raises(DepartureAirportNotFoundError):
        use_case.execute(command)

    assert repo.list_all() == []
    assert uow.commits == 0
    assert publisher.published == []


def test_airport_service_caido_no_hace_commit_ni_publica():
    use_case, _, uow, publisher, _ = _use_case(catalog=FakeAirportCatalog(unavailable=True))
    command = _command()

    with pytest.raises(AirportServiceUnavailableError):
        use_case.execute(command)

    assert uow.commits == 0
    assert publisher.published == []


def test_fallo_al_publicar_devuelve_el_itinerario_guardado(caplog):
    """Double write: el itinerario queda guardado aunque el evento se pierda."""
    use_case, repo, uow, publisher, _ = _use_case(publisher_fails=True)

    with caplog.at_level(logging.ERROR, logger="app.application.use_cases"):
        itinerary = use_case.execute(_command())

    assert repo.get_by_id(itinerary.id) is itinerary
    assert uow.commits == 1
    assert publisher.published == []
    assert "Evento perdido" in caplog.text
    assert str(itinerary.id) in caplog.text
