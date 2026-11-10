"""Pruebas de OutboxMessage: el mensaje pendiente creado a partir del evento (ADR-024)."""

from datetime import datetime, timedelta, timezone

from app.application.events import ItineraryCreatedEvent
from app.application.outbox import AGGREGATE_TYPE_ITINERARY, OutboxMessage
from app.domain.itinerary import Itinerary


def _event() -> ItineraryCreatedEvent:
    itinerary = Itinerary.create(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=datetime.now(timezone.utc) + timedelta(days=30),
        duration_minutes=75,
        traveler_email="ana@example.com",
    )
    return ItineraryCreatedEvent.from_itinerary(itinerary, "cid-1")


def test_el_id_del_mensaje_es_el_event_id():
    event = _event()

    message = OutboxMessage.from_event(event)

    assert message.id == event.event_id


def test_identifica_el_agregado_y_el_tipo_de_evento():
    event = _event()

    message = OutboxMessage.from_event(event)

    assert message.aggregate_type == AGGREGATE_TYPE_ITINERARY == "itinerary"
    assert message.aggregate_id == event.itinerary_id
    assert message.event_type == "itinerary.created"
    assert message.event_version == 1
    assert message.occurred_at == event.occurred_at


def test_el_payload_es_el_contrato_completo():
    event = _event()

    message = OutboxMessage.from_event(event)

    assert message.payload == event.to_dict()


def test_nace_pendiente_y_sin_intentos():
    message = OutboxMessage.from_event(_event())

    assert message.published_at is None
    assert message.attempts == 0
    assert message.last_error is None
    assert message.failed_at is None
