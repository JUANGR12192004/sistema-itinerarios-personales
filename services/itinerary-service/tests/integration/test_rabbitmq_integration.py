"""Prueba de integración de RabbitMQEventPublisher contra un RabbitMQ real.

Se omite (SKIPPED) si RabbitMQ no está disponible en RABBITMQ_URL.
Para ejecutarla en local:

    docker run -d --name itinerary-rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.13-management

ATENCIÓN: el fixture rabbitmq_channel (tests/integration/conftest.py) vacía (purge) la cola
notification.itinerary-created antes y después de la prueba.
"""

import json
from datetime import datetime, timedelta, timezone

from app.application.events import ItineraryCreatedEvent
from app.config import get_settings
from app.domain.itinerary import Itinerary
from app.infrastructure.messaging.rabbitmq_event_publisher import RabbitMQEventPublisher
from tests.integration.conftest import QUEUE_NOTIFICATIONS, RABBITMQ_TIMEOUT_SECONDS


def test_el_evento_llega_a_la_cola_de_notificaciones(rabbitmq_channel):
    itinerary = Itinerary.create(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=datetime.now(timezone.utc) + timedelta(days=30),
        duration_minutes=75,
    )
    event = ItineraryCreatedEvent.from_itinerary(itinerary, "cid-integration")
    publisher = RabbitMQEventPublisher(get_settings().rabbitmq_url, RABBITMQ_TIMEOUT_SECONDS)

    publisher.publish(event)

    method, properties, body = rabbitmq_channel.basic_get(QUEUE_NOTIFICATIONS, auto_ack=True)
    assert method is not None, "La cola no recibió el mensaje"
    assert json.loads(body) == event.to_dict()
    assert properties.message_id == str(event.event_id)
    assert properties.delivery_mode == 2
