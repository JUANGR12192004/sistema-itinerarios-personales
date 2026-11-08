"""Pruebas del contrato de ItineraryCreatedEvent (versión 1).

El evento es un contrato público: estas pruebas fallan si alguien cambia su forma
sin crear una versión nueva, protegiendo a los consumidores (Fase 6).
"""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from app.application.events import ItineraryCreatedEvent
from app.domain.itinerary import Itinerary

BOGOTA = timezone(timedelta(hours=-5))
FUTURE = datetime.now(BOGOTA).replace(microsecond=0) + timedelta(days=30)


def _itinerary(traveler_email: str | None = "ana@example.com") -> Itinerary:
    return Itinerary.create(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=FUTURE,
        duration_minutes=75,
        traveler_email=traveler_email,
    )


def test_el_contrato_tiene_exactamente_los_campos_acordados():
    payload = ItineraryCreatedEvent.from_itinerary(_itinerary(), "cid-1").to_dict()

    assert set(payload) == {
        "event_id", "event_type", "event_version", "occurred_at",
        "producer", "correlation_id", "data",
    }
    assert set(payload["data"]) == {
        "itinerary_id", "traveler_name", "traveler_email", "departure_airport_id",
        "arrival_airport_id", "travel_date", "duration_minutes",
    }


def test_metadatos_del_evento():
    payload = ItineraryCreatedEvent.from_itinerary(_itinerary(), "cid-1").to_dict()

    assert payload["event_type"] == "itinerary.created"
    assert payload["event_version"] == 1
    assert payload["producer"] == "itinerary-service"
    assert payload["correlation_id"] == "cid-1"
    UUID(payload["event_id"])  # lanza ValueError si no es un UUID válido


def test_datos_copian_el_itinerario():
    itinerary = _itinerary()
    data = ItineraryCreatedEvent.from_itinerary(itinerary).to_dict()["data"]

    assert data["itinerary_id"] == str(itinerary.id)
    assert data["traveler_name"] == "Ana Pérez"
    assert data["traveler_email"] == "ana@example.com"
    assert data["departure_airport_id"] == 1
    assert data["arrival_airport_id"] == 5
    assert data["duration_minutes"] == 75


def test_travel_date_conserva_la_zona_horaria_del_viajero():
    data = ItineraryCreatedEvent.from_itinerary(_itinerary()).to_dict()["data"]

    assert data["travel_date"].endswith("-05:00")
    assert datetime.fromisoformat(data["travel_date"]) == FUTURE


def test_occurred_at_va_en_utc_con_sufijo_z():
    occurred_at = ItineraryCreatedEvent.from_itinerary(_itinerary()).to_dict()["occurred_at"]

    assert occurred_at.endswith("Z")


def test_traveler_email_opcional_viaja_como_null():
    data = ItineraryCreatedEvent.from_itinerary(_itinerary(traveler_email=None)).to_dict()["data"]

    assert data["traveler_email"] is None


def test_sin_correlation_id_se_genera_uno():
    event = ItineraryCreatedEvent.from_itinerary(_itinerary(), None)

    UUID(event.correlation_id)


def test_cada_evento_tiene_un_event_id_distinto():
    itinerary = _itinerary()

    first = ItineraryCreatedEvent.from_itinerary(itinerary)
    second = ItineraryCreatedEvent.from_itinerary(itinerary)

    assert first.event_id != second.event_id


def test_el_evento_es_inmutable():
    event = ItineraryCreatedEvent.from_itinerary(_itinerary())

    with pytest.raises(FrozenInstanceError):
        event.traveler_name = "Otro"  # type: ignore[misc]


# ── from_dict (Fase 5): el relay reconstruye el evento guardado en la outbox ──

@pytest.mark.parametrize("traveler_email", ["ana@example.com", None])
def test_from_dict_es_la_inversa_de_to_dict(traveler_email):
    """Pasar por la outbox no cambia el contrato: to_dict(from_dict(p)) == p."""
    original = ItineraryCreatedEvent.from_itinerary(_itinerary(traveler_email), "cid-1")
    payload = original.to_dict()

    rebuilt = ItineraryCreatedEvent.from_dict(payload)

    assert rebuilt == original
    assert rebuilt.to_dict() == payload


def test_from_dict_rechaza_otro_tipo_de_evento():
    payload = ItineraryCreatedEvent.from_itinerary(_itinerary()).to_dict()
    payload["event_type"] = "itinerary.deleted"

    with pytest.raises(ValueError, match="Tipo de evento inesperado"):
        ItineraryCreatedEvent.from_dict(payload)


def test_from_dict_rechaza_otra_version():
    payload = ItineraryCreatedEvent.from_itinerary(_itinerary()).to_dict()
    payload["event_version"] = 2

    with pytest.raises(ValueError, match="Versión de evento no soportada"):
        ItineraryCreatedEvent.from_dict(payload)


def test_from_dict_sin_un_campo_lanza_key_error():
    payload = ItineraryCreatedEvent.from_itinerary(_itinerary()).to_dict()
    del payload["data"]["itinerary_id"]

    with pytest.raises(KeyError):
        ItineraryCreatedEvent.from_dict(payload)
