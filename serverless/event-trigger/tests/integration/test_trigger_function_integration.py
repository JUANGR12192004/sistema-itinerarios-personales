"""Integración del trigger con la función real (RIE en el puerto 9000) y RabbitMQ real.

SKIPPED si falta alguno. La función necesita notification-postgres con la migración aplicada.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.application.invocation import InvocationOutcome
from app.infrastructure.rabbitmq.topology import DEAD_LETTER_QUEUE, QUEUE_NOTIFICATIONS
from tests.integration.conftest import message_count, publish_event, run_trigger


def new_event(**data_overrides) -> dict:
    """ItineraryCreatedEvent v1 con un event_id nuevo (no estará en el historial)."""
    data = {
        "itinerary_id": str(uuid4()),
        "traveler_name": "Ana Pérez",
        "traveler_email": "ana@example.com",
        "departure_airport_id": 1,
        "arrival_airport_id": 5,
        "travel_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "duration_minutes": 75,
    }
    data.update(data_overrides)
    return {
        "event_id": str(uuid4()),
        "event_type": "itinerary.created",
        "event_version": 1,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "producer": "itinerary-service",
        "correlation_id": str(uuid4()),
        "data": data,
    }


def test_la_funcion_real_procesa_y_despues_reconoce_el_duplicado(function_invoker):
    event = new_event()

    first = function_invoker.invoke(event)
    second = function_invoker.invoke(event)

    assert (first.outcome, first.detail) == (InvocationOutcome.SUCCESS, "PROCESSED")
    assert (second.outcome, second.detail) == (InvocationOutcome.SUCCESS, "ALREADY_PROCESSED")


def test_la_funcion_real_rechaza_un_evento_invalido(function_invoker):
    result = function_invoker.invoke(new_event(duration_minutes=0))

    assert result.outcome is InvocationOutcome.REJECTED
    assert "duration_minutes" in result.detail


def test_de_punta_a_punta_el_evento_se_procesa_y_se_confirma(rabbitmq_channel, function_invoker):
    event = new_event()
    publish_event(rabbitmq_channel, event)

    assert run_trigger(function_invoker) == 1

    assert message_count(rabbitmq_channel, QUEUE_NOTIFICATIONS, 0) == 0
    assert message_count(rabbitmq_channel, DEAD_LETTER_QUEUE, 0) == 0
    # La función ya lo registró: invocarla otra vez con el mismo evento es un duplicado
    assert function_invoker.invoke(event).detail == "ALREADY_PROCESSED"


def test_de_punta_a_punta_un_duplicado_tambien_se_confirma(rabbitmq_channel, function_invoker):
    event = new_event()
    publish_event(rabbitmq_channel, event)
    publish_event(rabbitmq_channel, event)  # la misma copia dos veces (entrega al menos una vez)

    assert run_trigger(function_invoker, max_messages=2) == 2

    assert message_count(rabbitmq_channel, QUEUE_NOTIFICATIONS, 0) == 0
    assert message_count(rabbitmq_channel, DEAD_LETTER_QUEUE, 0) == 0


def test_de_punta_a_punta_un_evento_invalido_termina_en_la_dlq(rabbitmq_channel, function_invoker):
    publish_event(rabbitmq_channel, new_event(itinerary_id="no-es-un-uuid"))

    run_trigger(function_invoker)

    assert message_count(rabbitmq_channel, QUEUE_NOTIFICATIONS, 0) == 0
    assert message_count(rabbitmq_channel, DEAD_LETTER_QUEUE, 1) == 1
