"""Fixtures para las pruebas de integración del trigger (SKIPPED si falta el servicio).

AISLAMIENTO: las pruebas NO tocan la cola real notification.itinerary-created ni su DLQ.
Usan su propia topología con nombres únicos (prefijo `test-<id>.`), con los mismos argumentos
que la real: se declara una vez por sesión de pytest, sus colas (de prueba) se vacían antes y
después de cada prueba, y se borra al terminar la sesión. Así se pueden correr durante una
demostración sin vaciar ni consumir los mensajes de las colas reales.

Se declara una sola vez porque en RabbitMQ declarar y borrar colas tarda varios segundos.

rabbitmq_parameters — parámetros de conexión; SKIPPED (una sola vez) si RabbitMQ no responde.
rabbitmq_channel    — canal real para cada prueba.
test_topology       — topología de prueba con las colas vacías.
function_invoker    — LambdaFunctionInvoker contra la función real (RIE en el puerto 9000).
"""

import json
import time
from uuid import uuid4

import pika
import pytest
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPError

from app.application.delivery_handler import DeliveryHandler, RetryPolicy
from app.application.invocation import InvocationOutcome
from app.application.ports import FunctionInvoker
from app.config import get_settings
from app.infrastructure.lambda_invoker import LambdaFunctionInvoker
from app.infrastructure.rabbitmq.consumer import RabbitMQConsumer
from app.infrastructure.rabbitmq.topology import QueueTopology, declare_topology

# Esperas cortas para que las pruebas no dependan de servicios lentos o caídos
RABBITMQ_TIMEOUT_SECONDS = 2.0
FUNCTION_TIMEOUT_SECONDS = 5.0

# Política sin esperas: las pruebas comprueban las decisiones, no el tiempo
FAST_POLICY = RetryPolicy(
    infrastructure_attempts=2,
    function_error_attempts=2,
    backoff_seconds=0,
    max_backoff_seconds=0,
    requeue_delay_seconds=0,
)


@pytest.fixture(scope="session")
def rabbitmq_parameters() -> pika.URLParameters:
    """Comprueba una vez si RabbitMQ responde; si no, todas las pruebas que lo usan quedan SKIPPED."""
    parameters = pika.URLParameters(get_settings().rabbitmq_url)
    parameters.socket_timeout = RABBITMQ_TIMEOUT_SECONDS
    parameters.stack_timeout = RABBITMQ_TIMEOUT_SECONDS
    parameters.connection_attempts = 1
    try:
        pika.BlockingConnection(parameters).close()
    except (AMQPError, OSError):
        pytest.skip("RabbitMQ no disponible — omitiendo prueba de integración")
    return parameters


@pytest.fixture
def rabbitmq_channel(rabbitmq_parameters):
    connection = pika.BlockingConnection(rabbitmq_parameters)
    yield connection.channel()
    if connection.is_open:
        connection.close()


@pytest.fixture(scope="session")
def _session_topology(rabbitmq_parameters):
    """Topología con nombres únicos para esta sesión; se borra al final, pase lo que pase."""
    prefix = f"test-{uuid4().hex[:8]}."
    topology = QueueTopology(
        exchange=prefix + "itinerary.events",
        routing_key="itinerary.created",
        queue=prefix + "notification.itinerary-created",
        dead_letter_exchange=prefix + "itinerary.events.dlx",
        dead_letter_queue=prefix + "notification.itinerary-created.dlq",
    )
    connection = pika.BlockingConnection(rabbitmq_parameters)
    declare_topology(connection.channel(), topology)
    connection.close()
    try:
        yield topology
    finally:
        _delete_topology(rabbitmq_parameters, topology)


@pytest.fixture
def test_topology(rabbitmq_channel, _session_topology):
    """La topología de prueba con sus dos colas vacías (solo se vacían las colas de prueba)."""
    _purge(rabbitmq_channel, _session_topology)
    yield _session_topology
    if rabbitmq_channel.is_open:
        _purge(rabbitmq_channel, _session_topology)


def _purge(channel: BlockingChannel, topology: QueueTopology) -> None:
    channel.queue_purge(topology.queue)
    channel.queue_purge(topology.dead_letter_queue)


def _delete_topology(parameters: pika.URLParameters, topology: QueueTopology) -> None:
    """Borra las colas y exchanges de prueba con una conexión nueva."""
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_delete(queue=topology.queue)
    channel.queue_delete(queue=topology.dead_letter_queue)
    channel.exchange_delete(exchange=topology.exchange)
    channel.exchange_delete(exchange=topology.dead_letter_exchange)
    connection.close()


@pytest.fixture(scope="session")
def function_invoker():
    """Invocador de la función real. Si el RIE no responde, la prueba queda SKIPPED."""
    invoker = LambdaFunctionInvoker(get_settings().function_invoke_url, FUNCTION_TIMEOUT_SECONDS)
    # Un evento vacío no tiene efectos: la función lo rechaza sin tocar la base de datos
    if invoker.invoke({}).outcome is InvocationOutcome.INFRASTRUCTURE_ERROR:
        invoker.close()
        pytest.skip("SendNotificationFunction no disponible en FUNCTION_INVOKE_URL")
    yield invoker
    invoker.close()


def publish(channel: BlockingChannel, topology: QueueTopology, body: bytes, message_id: str | None = None) -> str:
    """Publica en el exchange de prueba como lo hace Itinerary Service y devuelve el message_id."""
    message_id = message_id or str(uuid4())
    channel.basic_publish(
        exchange=topology.exchange,
        routing_key=topology.routing_key,
        body=body,
        properties=pika.BasicProperties(
            message_id=message_id, delivery_mode=2, content_type="application/json", correlation_id="cid-test"
        ),
    )
    return message_id


def publish_event(channel: BlockingChannel, topology: QueueTopology, event: dict) -> str:
    return publish(channel, topology, json.dumps(event).encode("utf-8"), event.get("event_id"))


def run_trigger(invoker: FunctionInvoker, topology: QueueTopology, max_messages: int = 1) -> int:
    """Ejecuta el consumidor real sobre la topología de prueba hasta procesar `max_messages`
    o quedar la cola vacía."""
    consumer = RabbitMQConsumer(
        get_settings().rabbitmq_url,
        RABBITMQ_TIMEOUT_SECONDS,
        handler_factory=lambda sleep: DeliveryHandler(invoker, FAST_POLICY, sleep),
        topology=topology,
    )
    return consumer.run(max_messages=max_messages, stop_when_idle=True)


def message_count(channel: BlockingChannel, queue: str, expected: int, timeout_seconds: float = 3.0) -> int:
    """Cantidad de mensajes listos en la cola; espera un poco a que RabbitMQ la actualice."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        count = channel.queue_declare(queue=queue, passive=True).method.message_count
        if count == expected or time.monotonic() > deadline:
            return count
        time.sleep(0.1)
