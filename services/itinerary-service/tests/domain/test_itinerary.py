"""Pruebas del dominio de Itinerary: create(), update() y reglas de negocio."""

from datetime import datetime, timedelta, timezone

import pytest

from app.domain.exceptions import InvalidItineraryError
from app.domain.itinerary import Itinerary

FUTURE = datetime.now(timezone.utc) + timedelta(days=30)


# ——— Pruebas de create ———

def test_create_itinerary_valido():
    it = Itinerary.create(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=FUTURE,
        duration_minutes=75,
    )
    assert it.traveler_name == "Ana Pérez"
    assert it.departure_airport_id == 1
    assert it.arrival_airport_id == 5
    assert it.duration_minutes == 75
    assert it.traveler_email is None
    assert it.id is not None
    assert it.created_at is not None
    assert it.updated_at == it.created_at


def test_create_con_email_opcional():
    it = Itinerary.create(
        traveler_name="Carlos López",
        departure_airport_id=2,
        arrival_airport_id=8,
        travel_date=FUTURE,
        duration_minutes=120,
        traveler_email="carlos@example.com",
    )
    assert it.traveler_email == "carlos@example.com"


def test_create_normaliza_espacios_en_nombre():
    it = Itinerary.create(
        traveler_name="  María Torres  ",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=FUTURE,
        duration_minutes=60,
    )
    assert it.traveler_name == "María Torres"


def test_create_ids_unicos():
    it1 = Itinerary.create(
        traveler_name="Viajero Uno",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=FUTURE,
        duration_minutes=60,
    )
    it2 = Itinerary.create(
        traveler_name="Viajero Dos",
        departure_airport_id=2,
        arrival_airport_id=7,
        travel_date=FUTURE,
        duration_minutes=90,
    )
    assert it1.id != it2.id


def test_create_nombre_solo_espacios_lanza_error():
    with pytest.raises(InvalidItineraryError, match="nombre"):
        Itinerary.create(
            traveler_name="   ",
            departure_airport_id=1,
            arrival_airport_id=5,
            travel_date=FUTURE,
            duration_minutes=75,
        )


def test_create_nombre_vacio_lanza_error():
    with pytest.raises(InvalidItineraryError):
        Itinerary.create(
            traveler_name="",
            departure_airport_id=1,
            arrival_airport_id=5,
            travel_date=FUTURE,
            duration_minutes=75,
        )


def test_create_mismos_aeropuertos_lanza_error():
    with pytest.raises(InvalidItineraryError, match="diferentes"):
        Itinerary.create(
            traveler_name="Ana Pérez",
            departure_airport_id=3,
            arrival_airport_id=3,
            travel_date=FUTURE,
            duration_minutes=75,
        )


def test_create_duracion_cero_lanza_error():
    with pytest.raises(InvalidItineraryError, match="duración"):
        Itinerary.create(
            traveler_name="Ana Pérez",
            departure_airport_id=1,
            arrival_airport_id=5,
            travel_date=FUTURE,
            duration_minutes=0,
        )


def test_create_duracion_negativa_lanza_error():
    with pytest.raises(InvalidItineraryError):
        Itinerary.create(
            traveler_name="Ana Pérez",
            departure_airport_id=1,
            arrival_airport_id=5,
            travel_date=FUTURE,
            duration_minutes=-10,
        )


def test_create_fecha_en_el_pasado_lanza_error():
    pasado = datetime.now(timezone.utc) - timedelta(days=1)
    with pytest.raises(InvalidItineraryError, match="pasado"):
        Itinerary.create(
            traveler_name="Ana Pérez",
            departure_airport_id=1,
            arrival_airport_id=5,
            travel_date=pasado,
            duration_minutes=75,
        )


def test_create_fecha_sin_zona_horaria_lanza_error():
    naive = datetime.now() + timedelta(days=30)
    with pytest.raises(InvalidItineraryError, match="zona horaria"):
        Itinerary.create(
            traveler_name="Ana Pérez",
            departure_airport_id=1,
            arrival_airport_id=5,
            travel_date=naive,
            duration_minutes=75,
        )


# ——— Pruebas de update ———

def test_update_valido():
    it = Itinerary.create(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=FUTURE,
        duration_minutes=75,
    )
    # Fija las marcas de tiempo en el pasado para que update() produzca un valor posterior.
    # Necesario en Windows: el reloj tiene ~15 ms de resolución y create() + update()
    # pueden obtener el mismo datetime.now() si se ejecutan en el mismo tick.
    pasado_conocido = datetime.now(timezone.utc) - timedelta(seconds=1)
    it.created_at = pasado_conocido
    it.updated_at = pasado_conocido

    nueva_fecha = FUTURE + timedelta(days=1)
    it.update(
        traveler_name="Ana García",
        departure_airport_id=2,
        arrival_airport_id=6,
        travel_date=nueva_fecha,
        duration_minutes=90,
        traveler_email="ana@example.com",
    )
    assert it.traveler_name == "Ana García"
    assert it.departure_airport_id == 2
    assert it.arrival_airport_id == 6
    assert it.duration_minutes == 90
    assert it.traveler_email == "ana@example.com"
    assert it.updated_at > it.created_at


def test_update_permite_fecha_en_el_pasado():
    """Al actualizar no se verifica que la fecha no esté en el pasado (regla solo de creación)."""
    it = Itinerary.create(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=FUTURE,
        duration_minutes=75,
    )
    pasado = datetime.now(timezone.utc) - timedelta(days=1)
    it.update(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=pasado,
        duration_minutes=75,
    )
    assert it.travel_date == pasado


def test_update_preserva_id_y_created_at():
    it = Itinerary.create(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=FUTURE,
        duration_minutes=75,
    )
    original_id = it.id
    original_created_at = it.created_at
    it.update(
        traveler_name="Carlos",
        departure_airport_id=2,
        arrival_airport_id=6,
        travel_date=FUTURE,
        duration_minutes=90,
    )
    assert it.id == original_id
    assert it.created_at == original_created_at


def test_update_mismos_aeropuertos_lanza_error():
    it = Itinerary.create(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=FUTURE,
        duration_minutes=75,
    )
    with pytest.raises(InvalidItineraryError):
        it.update(
            traveler_name="Ana Pérez",
            departure_airport_id=3,
            arrival_airport_id=3,
            travel_date=FUTURE,
            duration_minutes=75,
        )


def test_update_nombre_vacio_lanza_error():
    it = Itinerary.create(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=FUTURE,
        duration_minutes=75,
    )
    with pytest.raises(InvalidItineraryError):
        it.update(
            traveler_name="",
            departure_airport_id=1,
            arrival_airport_id=5,
            travel_date=FUTURE,
            duration_minutes=75,
        )
