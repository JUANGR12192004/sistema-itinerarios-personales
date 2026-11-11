"""Pruebas de RabbitMQEventPublisher y de la topología con una conexión falsa (sin RabbitMQ).

La conexión falsa se inyecta con `connection_factory` y registra cada llamada que el
publicador hace al canal, así se verifica QUÉ se envía y en QUÉ orden.
"""

import json
from datetime import datetime, timedelta, timezone

import pika
import pytest
from pika.exceptions import AMQPConnectionError, ChannelClosedByBroker, UnroutableError

from app.application.events import ItineraryCreatedEvent
from app.application.exceptions import EventPublishError
from app.domain.itinerary import Itinerary
from app.infrastructure.messaging.rabbitmq_event_publisher import RabbitMQEventPublisher
from app.infrastructure.messaging.topology import (
    EXCHANGE,
    ROUTING_KEY_ITINERARY_CREATED,
    declare_exchange,
)

URL = "amqp://guest:guest@rabbitmq.local:5672/%2F"


class FakeChannel:
    """Canal falso: guarda (método, argumentos) de cada llamada."""

    def __init__(self, publish_error: Exception | None = None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._publish_error = publish_error

    def confirm_delivery(self) -> None:
        self.calls.append(("confirm_delivery", {}))

    def exchange_declare(self, **kwargs) -> None:
        self.calls.append(("exchange_declare", kwargs))

    def queue_declare(self, **kwargs) -> None:
        self.calls.append(("queue_declare", kwargs))

    def queue_bind(self, **kwargs) -> None:
        self.calls.append(("queue_bind", kwargs))

    def basic_publish(self, **kwargs) -> None:
        self.calls.append(("basic_publish", kwargs))
        if self._publish_error is not None:
            raise self._publish_error

    def names(self) -> list[str]:
        return [name for name, _ in self.calls]

    def first(self, name: str) -> dict:
        return next(kwargs for call_name, kwargs in self.calls if call_name == name)


class FakeConnection:
    def __init__(self, channel: FakeChannel) -> None:
        self._channel = channel
        self.is_open = True
        self.closed = False

    def channel(self) -> FakeChannel:
        return self._channel

    def close(self) -> None:
        self.closed = True
        self.is_open = False


def _event() -> ItineraryCreatedEvent:
    itinerary = Itinerary.create(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=datetime.now(timezone.utc) + timedelta(days=30),
        duration_minutes=75,
        traveler_email="ana@example.com",
    )
    return ItineraryCreatedEvent.from_itinerary(itinerary, "cid-77")


def _publisher(channel: FakeChannel) -> tuple[RabbitMQEventPublisher, FakeConnection, list]:
    connection = FakeConnection(channel)
    received_parameters: list = []

    def factory(parameters):
        received_parameters.append(parameters)
        return connection

    return RabbitMQEventPublisher(URL, 2.5, connection_factory=factory), connection, received_parameters


# ——— Publicación exitosa ———

def test_publica_en_el_exchange_con_la_routing_key():
    channel = FakeChannel()
    publisher, _, _ = _publisher(channel)

    publisher.publish(_event())

    publish = channel.first("basic_publish")
    assert publish["exchange"] == EXCHANGE == "itinerary.events"
    assert publish["routing_key"] == ROUTING_KEY_ITINERARY_CREATED == "itinerary.created"
    assert publish["mandatory"] is True


def test_el_cuerpo_es_el_contrato_en_json_utf8():
    channel = FakeChannel()
    publisher, _, _ = _publisher(channel)
    event = _event()

    publisher.publish(event)

    body = channel.first("basic_publish")["body"]
    assert json.loads(body.decode("utf-8")) == event.to_dict()
    assert "Pérez".encode("utf-8") in body  # las tildes viajan sin escapar


def test_propiedades_del_mensaje():
    channel = FakeChannel()
    publisher, _, _ = _publisher(channel)
    event = _event()

    publisher.publish(event)

    properties: pika.BasicProperties = channel.first("basic_publish")["properties"]
    assert properties.delivery_mode == 2  # persistente
    assert properties.content_type == "application/json"
    assert properties.message_id == str(event.event_id)
    assert properties.correlation_id == "cid-77"
    assert properties.type == "itinerary.created"
    assert properties.app_id == "itinerary-service"
    assert properties.headers == {"event_version": 1}


def test_activa_confirms_y_declara_el_exchange_antes_de_publicar():
    channel = FakeChannel()
    publisher, _, _ = _publisher(channel)

    publisher.publish(_event())

    assert channel.names() == ["confirm_delivery", "exchange_declare", "basic_publish"]


def test_cierra_la_conexion_despues_de_publicar():
    channel = FakeChannel()
    publisher, connection, _ = _publisher(channel)

    publisher.publish(_event())

    assert connection.closed is True


def test_configura_timeouts_y_un_solo_intento_de_conexion():
    publisher, _, received = _publisher(FakeChannel())

    publisher.publish(_event())

    parameters = received[0]
    assert parameters.host == "rabbitmq.local"
    assert parameters.socket_timeout == 2.5
    assert parameters.stack_timeout == 2.5
    assert parameters.blocked_connection_timeout == 2.5
    assert parameters.connection_attempts == 1


# ——— Fallos: siempre EventPublishError ———

def test_rabbitmq_caido_lanza_event_publish_error():
    def factory(_parameters):
        raise AMQPConnectionError("connection refused")

    publisher = RabbitMQEventPublisher(URL, 2.5, connection_factory=factory)
    event = _event()

    with pytest.raises(EventPublishError) as exc_info:
        publisher.publish(event)
    assert isinstance(exc_info.value.__cause__, AMQPConnectionError)


def test_error_de_red_lanza_event_publish_error():
    def factory(_parameters):
        raise OSError("network unreachable")

    publisher = RabbitMQEventPublisher(URL, 2.5, connection_factory=factory)
    event = _event()

    with pytest.raises(EventPublishError):
        publisher.publish(event)


def test_mensaje_sin_cola_destino_lanza_error_y_cierra_la_conexion():
    """mandatory=True: si ninguna cola recibe el mensaje, RabbitMQ lo devuelve (UnroutableError)."""
    channel = FakeChannel(publish_error=UnroutableError([]))
    publisher, connection, _ = _publisher(channel)
    event = _event()

    with pytest.raises(EventPublishError):
        publisher.publish(event)
    assert connection.closed is True


def test_canal_cerrado_por_rabbitmq_lanza_event_publish_error():
    """Por ejemplo, PRECONDITION_FAILED si la cola existe con otros argumentos."""
    channel = FakeChannel(publish_error=ChannelClosedByBroker(406, "PRECONDITION_FAILED"))
    publisher, connection, _ = _publisher(channel)
    event = _event()

    with pytest.raises(EventPublishError):
        publisher.publish(event)
    assert connection.closed is True


# ——— Topología (ADR-032: el productor declara solo su exchange) ———

def test_declara_el_exchange_topic_durable():
    channel = FakeChannel()

    declare_exchange(channel)

    assert channel.calls == [
        ("exchange_declare", {"exchange": "itinerary.events", "exchange_type": "topic", "durable": True}),
    ]


def test_el_publicador_no_declara_colas_ni_la_dlx():
    """La cola, su binding, la DLX y la DLQ son del Event Trigger (el consumidor)."""
    channel = FakeChannel()
    publisher, _, _ = _publisher(channel)

    publisher.publish(_event())

    names = channel.names()
    assert "queue_declare" not in names
    assert "queue_bind" not in names
    declared_exchanges = [kw["exchange"] for name, kw in channel.calls if name == "exchange_declare"]
    assert declared_exchanges == [EXCHANGE]
