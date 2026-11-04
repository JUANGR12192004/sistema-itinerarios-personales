"""Pruebas del contrato de ItineraryRepository y de los otros fakes.

Usan FakeItineraryRepository y FakeAirportCatalog (sin PostgreSQL ni red).
Sirven para:
  1. Verificar que los fakes se comportan según el contrato del puerto.
  2. Documentar cómo configurar los fakes en las pruebas de casos de uso (3D).
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.application.events import ItineraryCreatedEvent
from app.application.exceptions import (
    AirportNotFoundInCatalogError,
    AirportServiceTimeoutError,
    AirportServiceUnavailableError,
    EventPublishError,
)
from app.domain.itinerary import Itinerary
from tests.fakes import (
    FakeAirportCatalog,
    FakeEventPublisher,
    FakeItineraryRepository,
    FakeUnitOfWork,
)

FUTURE = datetime.now(timezone.utc) + timedelta(days=30)


def _crear_itinerario(**overrides) -> Itinerary:
    defaults = dict(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=FUTURE,
        duration_minutes=75,
    )
    defaults.update(overrides)
    return Itinerary.create(**defaults)


# ——— FakeItineraryRepository ———

def test_repo_save_y_get_by_id():
    repo = FakeItineraryRepository()
    it = _crear_itinerario()
    repo.save(it)
    resultado = repo.get_by_id(it.id)
    assert resultado is not None
    assert resultado.id == it.id
    assert resultado.traveler_name == "Ana Pérez"


def test_repo_get_by_id_no_encontrado_devuelve_none():
    repo = FakeItineraryRepository()
    assert repo.get_by_id(uuid4()) is None


def test_repo_list_all_vacio():
    repo = FakeItineraryRepository()
    assert repo.list_all() == []


def test_repo_list_all_devuelve_todos():
    repo = FakeItineraryRepository()
    repo.save(_crear_itinerario(traveler_name="Viajero Uno"))
    repo.save(_crear_itinerario(traveler_name="Viajero Dos", departure_airport_id=2, arrival_airport_id=6))
    assert len(repo.list_all()) == 2


def test_repo_save_sobreescribe_itinerario_existente():
    repo = FakeItineraryRepository()
    it = _crear_itinerario()
    repo.save(it)
    it.update(
        traveler_name="Nombre Actualizado",
        departure_airport_id=it.departure_airport_id,
        arrival_airport_id=it.arrival_airport_id,
        travel_date=it.travel_date,
        duration_minutes=it.duration_minutes,
    )
    repo.save(it)
    assert repo.get_by_id(it.id).traveler_name == "Nombre Actualizado"
    assert len(repo.list_all()) == 1


def test_repo_delete_elimina_itinerario():
    repo = FakeItineraryRepository()
    it = _crear_itinerario()
    repo.save(it)
    repo.delete(it.id)
    assert repo.get_by_id(it.id) is None
    assert len(repo.list_all()) == 0


def test_repo_delete_id_inexistente_no_lanza():
    repo = FakeItineraryRepository()
    repo.delete(uuid4())  # no debe lanzar excepción


# ——— FakeAirportCatalog ———

def test_catalog_todos_validos_por_defecto():
    catalog = FakeAirportCatalog()
    catalog.verify_exists(1)
    catalog.verify_exists(999)  # sin restricciones: cualquier id es válido


def test_catalog_id_no_existente_lanza_error():
    catalog = FakeAirportCatalog(existing_ids={1, 5})
    with pytest.raises(AirportNotFoundInCatalogError) as exc_info:
        catalog.verify_exists(99)
    assert exc_info.value.airport_id == 99


def test_catalog_no_disponible_lanza_error():
    catalog = FakeAirportCatalog(unavailable=True)
    with pytest.raises(AirportServiceUnavailableError):
        catalog.verify_exists(1)


def test_catalog_timeout_lanza_error():
    catalog = FakeAirportCatalog(timeout=True)
    with pytest.raises(AirportServiceTimeoutError):
        catalog.verify_exists(1)


def test_catalog_timeout_es_subclase_de_unavailable():
    """AirportServiceTimeoutError es subclase de AirportServiceUnavailableError."""
    catalog = FakeAirportCatalog(timeout=True)
    with pytest.raises(AirportServiceUnavailableError):
        catalog.verify_exists(1)


# ——— FakeEventPublisher ———

def test_publisher_registra_eventos_publicados():
    publisher = FakeEventPublisher()
    it = _crear_itinerario()
    publisher.publish(ItineraryCreatedEvent.from_itinerary(it))
    assert len(publisher.published) == 1
    assert publisher.published[0].itinerary_id == it.id


def test_publisher_acumula_multiples_eventos():
    publisher = FakeEventPublisher()
    publisher.publish(ItineraryCreatedEvent.from_itinerary(_crear_itinerario(traveler_name="Viajero 1")))
    publisher.publish(ItineraryCreatedEvent.from_itinerary(_crear_itinerario(traveler_name="Viajero 2", departure_airport_id=2, arrival_airport_id=6)))
    assert len(publisher.published) == 2


def test_publisher_con_fallo_lanza_event_publish_error():
    publisher = FakeEventPublisher(fail=True)
    event = ItineraryCreatedEvent.from_itinerary(_crear_itinerario())
    with pytest.raises(EventPublishError):
        publisher.publish(event)
    assert publisher.published == []


# ——— FakeUnitOfWork ———

def test_unit_of_work_cuenta_los_commits():
    uow = FakeUnitOfWork()
    uow.commit()
    uow.commit()
    assert uow.commits == 2
