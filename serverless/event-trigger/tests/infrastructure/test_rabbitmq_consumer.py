"""Pruebas del consumidor de RabbitMQ y de la topología con una conexión falsa (sin RabbitMQ)."""

from types import SimpleNamespace

import pytest

from app.application.delivery_handler import Decision
from app.infrastructure.rabbitmq.consumer import RabbitMQConsumer, apply_decision
from app.infrastructure.rabbitmq.topology import (
    DEAD_LETTER_EXCHANGE,
    DEAD_LETTER_QUEUE,
    EXCHANGE,
    QUEUE_NOTIFICATIONS,
    declare_topology,
)


class FakeChannel:
    """Canal falso: registra cada llamada y entrega los mensajes dados en consume()."""

    def __init__(self, deliveries: list | None = None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._deliveries = deliveries or []

    def __getattr__(self, name):
        # exchange_declare, queue_declare, queue_bind, basic_qos, basic_ack, basic_reject, basic_nack, cancel
        def record(**kwargs):
            self.calls.append((name, kwargs))

        return record

    def consume(self, queue, auto_ack, inactivity_timeout):
        self.calls.append(("consume", {"queue": queue, "auto_ack": auto_ack}))
        yield from self._deliveries

    def names(self) -> list[str]:
        return [name for name, _ in self.calls]


class FakeConnection:
    def __init__(self, channel: FakeChannel) -> None:
        self._channel = channel
        self.is_open = True
        self.sleeps: list[float] = []

    def channel(self) -> FakeChannel:
        return self._channel

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)

    def close(self) -> None:
        self.is_open = False


class FakeHandler:
    """Devuelve las decisiones dadas, en orden."""

    def __init__(self, *decisions: Decision) -> None:
        self._decisions = list(decisions)
        self.bodies: list[bytes] = []

    def handle(self, body: bytes, message_id: str | None = None, traceparent: str | None = None) -> Decision:
        self.bodies.append(body)
        return self._decisions.pop(0)


def delivery(tag: int, body: bytes = b"{}", headers: dict | None = None):
    return (
        SimpleNamespace(delivery_tag=tag, redelivered=False),
        SimpleNamespace(message_id=f"m-{tag}", headers=headers),
        body,
    )


IDLE = (None, None, None)  # lo que entrega consume() tras un segundo sin mensajes


def make_consumer(channel: FakeChannel, handler: FakeHandler):
    connection = FakeConnection(channel)
    received_sleep = []

    def handler_factory(sleep):
        received_sleep.append(sleep)
        return handler

    consumer = RabbitMQConsumer(
        "amqp://guest:guest@rabbitmq.local:5672/%2F",
        2.0,
        handler_factory=handler_factory,
        connection_factory=lambda parameters: connection,
    )
    return consumer, connection, received_sleep


# ——— apply_decision ———

@pytest.mark.parametrize(
    ("decision", "expected"),
    [
        (Decision.ACK, ("basic_ack", {"delivery_tag": 7})),
        (Decision.REJECT, ("basic_reject", {"delivery_tag": 7, "requeue": False})),
        (Decision.REQUEUE, ("basic_nack", {"delivery_tag": 7, "requeue": True})),
    ],
)
def test_cada_decision_se_traduce_a_la_respuesta_de_rabbitmq(decision, expected):
    channel = FakeChannel()

    apply_decision(channel, 7, decision)

    assert channel.calls == [expected]


# ——— Topología (ADR-032): mismos argumentos de ADR-021 ———

def test_topologia_del_consumidor_con_los_argumentos_de_adr_021():
    channel = FakeChannel()

    declare_topology(channel)

    assert ("exchange_declare", {"exchange": EXCHANGE, "exchange_type": "topic", "durable": True}) in channel.calls
    assert (
        "exchange_declare",
        {"exchange": DEAD_LETTER_EXCHANGE, "exchange_type": "direct", "durable": True},
    ) in channel.calls
    assert ("queue_declare", {"queue": DEAD_LETTER_QUEUE, "durable": True}) in channel.calls
    assert (
        "queue_declare",
        {
            "queue": QUEUE_NOTIFICATIONS,
            "durable": True,
            "arguments": {"x-dead-letter-exchange": "itinerary.events.dlx"},
        },
    ) in channel.calls
    assert (
        "queue_bind",
        {"queue": QUEUE_NOTIFICATIONS, "exchange": EXCHANGE, "routing_key": "itinerary.created"},
    ) in channel.calls
    assert (
        "queue_bind",
        {"queue": DEAD_LETTER_QUEUE, "exchange": DEAD_LETTER_EXCHANGE, "routing_key": "itinerary.created"},
    ) in channel.calls


def test_la_dlq_tambien_recibe_los_mensajes_reprocesados_que_vuelven_a_fallar():
    """Un mensaje devuelto por replay_dlq llega con routing key = nombre de la cola; si se
    rechaza otra vez, la DLX lo enruta con esa clave. Sin este binding se perdería."""
    channel = FakeChannel()

    declare_topology(channel)

    assert (
        "queue_bind",
        {"queue": DEAD_LETTER_QUEUE, "exchange": DEAD_LETTER_EXCHANGE, "routing_key": QUEUE_NOTIFICATIONS},
    ) in channel.calls


def test_nombres_de_la_topologia():
    assert EXCHANGE == "itinerary.events"
    assert QUEUE_NOTIFICATIONS == "notification.itinerary-created"
    assert DEAD_LETTER_EXCHANGE == "itinerary.events.dlx"
    assert DEAD_LETTER_QUEUE == "notification.itinerary-created.dlq"


# ——— RabbitMQConsumer.run ———

def test_declara_la_topologia_y_prefetch_1_antes_de_consumir():
    channel = FakeChannel([IDLE])
    consumer, _, _ = make_consumer(channel, FakeHandler())

    consumer.run(stop_when_idle=True)

    names = channel.names()
    assert names.index("queue_declare") < names.index("basic_qos") < names.index("consume")
    assert ("basic_qos", {"prefetch_count": 1}) in channel.calls
    assert ("consume", {"queue": QUEUE_NOTIFICATIONS, "auto_ack": False}) in channel.calls


def test_aplica_la_decision_de_cada_mensaje():
    channel = FakeChannel([delivery(1, b'{"a": 1}'), delivery(2), delivery(3)])
    handler = FakeHandler(Decision.ACK, Decision.REJECT, Decision.REQUEUE)
    consumer, _, _ = make_consumer(channel, handler)

    processed = consumer.run(max_messages=3)

    assert processed == 3
    assert handler.bodies[0] == b'{"a": 1}'
    assert ("basic_ack", {"delivery_tag": 1}) in channel.calls
    assert ("basic_reject", {"delivery_tag": 2, "requeue": False}) in channel.calls
    assert ("basic_nack", {"delivery_tag": 3, "requeue": True}) in channel.calls


def test_ignora_los_periodos_sin_mensajes_mientras_no_se_pida_parar():
    channel = FakeChannel([IDLE, IDLE, delivery(1)])
    consumer, _, _ = make_consumer(channel, FakeHandler(Decision.ACK))

    assert consumer.run(max_messages=1) == 1


def test_la_politica_espera_con_connection_sleep_y_la_conexion_se_cierra():
    channel = FakeChannel([IDLE])
    consumer, connection, received_sleep = make_consumer(channel, FakeHandler())

    consumer.run(stop_when_idle=True)

    assert received_sleep == [connection.sleep]  # atiende heartbeats mientras espera
    assert connection.is_open is False
