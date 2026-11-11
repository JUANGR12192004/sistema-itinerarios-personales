"""Pruebas de la validación del contrato v1 en el adaptador de entrada (ADR-028)."""

import json
from uuid import UUID

import pytest

from app.application.exceptions import InvalidEventError
from app.event_schema import parse_event
from tests.samples import EVENTS_DIR, event_payload


def test_un_evento_valido_se_convierte_al_objeto_de_aplicacion():
    payload = event_payload(event_id="7d9f1c2e-4b5a-4e8f-9a1b-2c3d4e5f6a7b")

    event = parse_event(payload)

    assert event.event_id == UUID("7d9f1c2e-4b5a-4e8f-9a1b-2c3d4e5f6a7b")
    assert event.itinerary_id == UUID(payload["data"]["itinerary_id"])
    assert event.traveler_name == "Ana Pérez"
    assert event.traveler_email == "ana@example.com"
    assert event.departure_airport_id == 1
    assert event.arrival_airport_id == 5
    assert event.duration_minutes == 75
    assert event.correlation_id == payload["correlation_id"]
    assert event.travel_date.utcoffset() is not None


def test_ignora_los_campos_que_no_conoce():
    payload = event_payload(seat="12A")
    payload["new_field"] = "compatible"

    assert parse_event(payload).traveler_name == "Ana Pérez"


@pytest.mark.parametrize("email", [None, "missing"])
def test_traveler_email_es_opcional(email):
    payload = event_payload()
    if email == "missing":
        del payload["data"]["traveler_email"]
    else:
        payload["data"]["traveler_email"] = email

    assert parse_event(payload).traveler_email is None


@pytest.mark.parametrize("raw", [None, "texto", ["lista"], 42])
def test_rechaza_lo_que_no_es_un_objeto_json(raw):
    with pytest.raises(InvalidEventError) as error:
        parse_event(raw)

    assert "objeto JSON" in error.value.reason
    assert error.value.event_id is None


def test_rechaza_un_event_type_desconocido_y_conserva_el_event_id():
    payload = event_payload(event_id="7d9f1c2e-4b5a-4e8f-9a1b-2c3d4e5f6a7b")
    payload["event_type"] = "itinerary.deleted"

    with pytest.raises(InvalidEventError) as error:
        parse_event(payload)

    assert "event_type desconocido" in error.value.reason
    assert error.value.event_id == UUID("7d9f1c2e-4b5a-4e8f-9a1b-2c3d4e5f6a7b")


def test_rechaza_una_version_no_soportada():
    payload = event_payload()
    payload["event_version"] = 2

    with pytest.raises(InvalidEventError) as error:
        parse_event(payload)

    assert "event_version no soportada" in error.value.reason


def test_rechaza_campos_invalidos_y_los_nombra():
    payload = event_payload(itinerary_id="no-es-un-uuid", travel_date="2026-12-15T08:00:00", duration_minutes=0)

    with pytest.raises(InvalidEventError) as error:
        parse_event(payload)

    reason = error.value.reason
    assert reason.startswith("El evento no cumple el contrato v1")
    assert "data.itinerary_id" in reason
    assert "data.travel_date" in reason  # fecha sin zona horaria (ADR-017)
    assert "data.duration_minutes" in reason


@pytest.mark.parametrize("field", ["departure_airport_id", "arrival_airport_id"])
def test_rechaza_ids_de_aeropuerto_menores_que_1(field):
    with pytest.raises(InvalidEventError):
        parse_event(event_payload(**{field: 0}))


def test_rechaza_un_nombre_de_viajero_vacio():
    with pytest.raises(InvalidEventError):
        parse_event(event_payload(traveler_name="   "))


def test_rechaza_un_evento_sin_data():
    payload = event_payload()
    del payload["data"]

    with pytest.raises(InvalidEventError) as error:
        parse_event(payload)

    assert "data" in error.value.reason


def test_si_el_event_id_es_invalido_el_error_no_tiene_event_id():
    payload = event_payload()
    payload["event_id"] = "no-es-un-uuid"

    with pytest.raises(InvalidEventError) as error:
        parse_event(payload)

    assert error.value.event_id is None


@pytest.mark.parametrize(
    "file_name", ["itinerary-created.json", "itinerary-created-without-email.json"]
)
def test_los_eventos_de_ejemplo_de_la_demostracion_son_validos(file_name):
    raw = json.loads((EVENTS_DIR / file_name).read_text(encoding="utf-8"))

    assert parse_event(raw).event_id == UUID(raw["event_id"])


def test_el_evento_invalido_de_la_demostracion_se_rechaza():
    raw = json.loads((EVENTS_DIR / "invalid-event.json").read_text(encoding="utf-8"))

    with pytest.raises(InvalidEventError):
        parse_event(raw)
