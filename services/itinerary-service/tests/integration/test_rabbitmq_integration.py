"""Prueba de integración de RabbitMQEventPublisher contra un RabbitMQ real.

Se omite (SKIPPED) si RabbitMQ no está disponible en RABBITMQ_URL.
Para ejecutarla en local:

    docker run -d --name itinerary-rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.13-management

Publica en una topología de prueba con nombres propios (fixture isolated_topology de
tests/integration/conftest.py): no toca la cola real notification.itinerary-created ni su DLQ.
"""

import json
from datetime import datetime, timedelta, timezone

from app.application.events import ItineraryCreatedEvent
from app.domain.itinerary import Itinerary


def test_el_evento_llega_a_la_cola_de_notificaciones(rabbitmq_channel, isolated_topology, isolated_publisher):
    itinerary = Itinerary.create(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=datetime.now(timezone.utc) + timedelta(days=30),
        duration_minutes=75,
    )
    event = ItineraryCreatedEvent.from_itinerary(itinerary, "cid-integration")

    isolated_publisher.publish(event)

    method, properties, body = rabbitmq_channel.basic_get(isolated_topology.queue, auto_ack=True)
    assert method is not None, "La cola no recibió el mensaje"
    assert json.loads(body) == event.to_dict()
    assert properties.message_id == str(event.event_id)
    assert properties.delivery_mode == 2
