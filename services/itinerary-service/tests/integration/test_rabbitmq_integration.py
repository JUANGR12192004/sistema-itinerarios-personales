"""Prueba de integración de RabbitMQEventPublisher contra un RabbitMQ real.

Se omite (SKIPPED) si RabbitMQ no está disponible en RABBITMQ_URL.
Para ejecutarla en local:

    docker run -d --name itinerary-rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.13-management

ATENCIÓN: vacía (purge) la cola notification.itinerary-created antes y después de la prueba.
No ejecutarla contra un RabbitMQ con mensajes que se quieran conservar.
"""

import json
from datetime import datetime, timedelta, timezone

import pika
import pytest
from pika.exceptions import AMQPError

from app.application.events import ItineraryCreatedEvent
from app.config import get_settings
from app.domain.itinerary import Itinerary
from app.infrastructure.messaging.rabbitmq_event_publisher import RabbitMQEventPublisher
from app.infrastructure.messaging.topology import QUEUE_NOTIFICATIONS, declare_topology

TIMEOUT_SECONDS = 2.0


@pytest.fixture
def rabbitmq_channel():
    """Canal real con la topología declarada y la cola vacía; SKIPPED si no hay RabbitMQ."""
    parameters = pika.URLParameters(get_settings().rabbitmq_url)
    parameters.socket_timeout = TIMEOUT_SECONDS
    parameters.stack_timeout = TIMEOUT_SECONDS
    parameters.connection_attempts = 1
    try:
        connection = pika.BlockingConnection(parameters)
    except (AMQPError, OSError):
        pytest.skip("RabbitMQ no disponible — omitiendo prueba de integración")

    channel = connection.channel()
    declare_topology(channel)
    channel.queue_purge(QUEUE_NOTIFICATIONS)

    yield channel

    channel.queue_purge(QUEUE_NOTIFICATIONS)
    connection.close()


def test_el_evento_llega_a_la_cola_de_notificaciones(rabbitmq_channel):
    itinerary = Itinerary.create(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=datetime.now(timezone.utc) + timedelta(days=30),
        duration_minutes=75,
    )
    event = ItineraryCreatedEvent.from_itinerary(itinerary, "cid-integration")
    publisher = RabbitMQEventPublisher(get_settings().rabbitmq_url, TIMEOUT_SECONDS)

    publisher.publish(event)

    method, properties, body = rabbitmq_channel.basic_get(QUEUE_NOTIFICATIONS, auto_ack=True)
    assert method is not None, "La cola no recibió el mensaje"
    assert json.loads(body) == event.to_dict()
    assert properties.message_id == str(event.event_id)
    assert properties.delivery_mode == 2
