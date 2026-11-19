"""Pruebas de UpdateItineraryUseCase y DeleteItineraryUseCase centradas en el commit.

Igual que al crear, el caso de uso confirma la transacción con UnitOfWork ANTES de
devolver el resultado: así la respuesta HTTP sale con los cambios ya guardados
(ADR-019). Si algo falla antes del commit, no se confirma nada.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.application.exceptions import ArrivalAirportNotFoundError, ItineraryNotFoundError
from app.application.use_cases import (
    DeleteItineraryUseCase,
    UpdateItineraryCommand,
    UpdateItineraryUseCase,
)
from app.domain.itinerary import Itinerary
from tests.fakes import FakeAirportCatalog, FakeItineraryRepository, FakeUnitOfWork

FUTURE = datetime.now(timezone.utc) + timedelta(days=30)


def _itinerary() -> Itinerary:
    return Itinerary.create(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=FUTURE,
        duration_minutes=75,
    )


def _command(**overrides) -> UpdateItineraryCommand:
    values = dict(
        traveler_name="Ana Actualizada",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=FUTURE,
        duration_minutes=90,
    )
    values.update(overrides)
    return UpdateItineraryCommand(**values)


def _repo_with(itinerary: Itinerary, calls: list[str]) -> FakeItineraryRepository:
    repo = FakeItineraryRepository(calls)
    repo.save(itinerary)
    calls.clear()  # solo interesan las llamadas del caso de uso
    return repo


# ── Actualizar ─────────────────────────────────────────────────────────────────

def test_actualizar_guarda_y_despues_confirma():
    calls: list[str] = []
    itinerary = _itinerary()
    repo = _repo_with(itinerary, calls)
    uow = FakeUnitOfWork(calls)

    result = UpdateItineraryUseCase(repo, FakeAirportCatalog(), uow).execute(
        itinerary.id, _command()
    )

    assert result.traveler_name == "Ana Actualizada"
    assert calls == ["save", "commit"]


def test_actualizar_inexistente_no_confirma():
    uow = FakeUnitOfWork()

    with pytest.raises(ItineraryNotFoundError):
        UpdateItineraryUseCase(FakeItineraryRepository(), FakeAirportCatalog(), uow).execute(
            uuid4(), _command()
        )

    assert uow.commits == 0


def test_actualizar_con_aeropuerto_inexistente_no_guarda_ni_confirma():
    calls: list[str] = []
    itinerary = _itinerary()
    repo = _repo_with(itinerary, calls)
    uow = FakeUnitOfWork(calls)
    catalog = FakeAirportCatalog(existing_ids={1})

    with pytest.raises(ArrivalAirportNotFoundError):
        UpdateItineraryUseCase(repo, catalog, uow).execute(itinerary.id, _command())

    assert calls == []


# ── Eliminar ───────────────────────────────────────────────────────────────────

def test_eliminar_borra_y_despues_confirma():
    calls: list[str] = []
    itinerary = _itinerary()
    repo = _repo_with(itinerary, calls)
    uow = FakeUnitOfWork(calls)

    DeleteItineraryUseCase(repo, uow).execute(itinerary.id)

    assert calls == ["delete", "commit"]
    assert repo.get_by_id(itinerary.id) is None


def test_eliminar_inexistente_no_confirma():
    calls: list[str] = []
    uow = FakeUnitOfWork(calls)

    with pytest.raises(ItineraryNotFoundError):
        DeleteItineraryUseCase(FakeItineraryRepository(calls), uow).execute(uuid4())

    assert calls == []
