"""Fixtures para las pruebas de integración del trigger (SKIPPED si falta el servicio).

rabbitmq_channel — canal real con la topología del trigger declarada y las colas vacías.
function_invoker — LambdaFunctionInvoker contra la función real (RIE en el puerto 9000).

ATENCIÓN: rabbitmq_channel vacía (purge) la cola notification.itinerary-created y la DLQ
antes y después de cada prueba. Detener el trigger (`python -m app.main`) antes de correr
estas pruebas y no usarlas contra un RabbitMQ con mensajes que se quieran conservar.
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
from app.infrastructure.rabbitmq.topology import (
    DEAD_LETTER_QUEUE,
    EXCHANGE,
    QUEUE_NOTIFICATIONS,
    ROUTING_KEY_ITINERARY_CREATED,
    declare_topology,
)

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


@pytest.fixture
def rabbitmq_channel():
    parameters = pika.URLParameters(get_settings().rabbitmq_url)
    parameters.socket_timeout = RABBITMQ_TIMEOUT_SECONDS
    parameters.stack_timeout = RABBITMQ_TIMEOUT_SECONDS
    parameters.connection_attempts = 1
    try:
        connection = pika.BlockingConnection(parameters)
    except (AMQPError, OSError):
        pytest.skip("RabbitMQ no disponible — omitiendo prueba de integración")

    channel = connection.channel()
    declare_topology(channel)
    _purge(channel)
    yield channel
    _purge(channel)
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


def _purge(channel: BlockingChannel) -> None:
    channel.queue_purge(QUEUE_NOTIFICATIONS)
    channel.queue_purge(DEAD_LETTER_QUEUE)


def publish(channel: BlockingChannel, body: bytes, message_id: str | None = None) -> str:
    """Publica en el exchange como lo hace Itinerary Service y devuelve el message_id."""
    message_id = message_id or str(uuid4())
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key=ROUTING_KEY_ITINERARY_CREATED,
        body=body,
        properties=pika.BasicProperties(message_id=message_id, delivery_mode=2),
    )
    return message_id


def publish_event(channel: BlockingChannel, event: dict) -> str:
    return publish(channel, json.dumps(event).encode("utf-8"), event.get("event_id"))


def run_trigger(invoker: FunctionInvoker, max_messages: int = 1) -> int:
    """Ejecuta el consumidor real hasta procesar `max_messages` o quedar la cola vacía."""
    consumer = RabbitMQConsumer(
        get_settings().rabbitmq_url,
        RABBITMQ_TIMEOUT_SECONDS,
        handler_factory=lambda sleep: DeliveryHandler(invoker, FAST_POLICY, sleep),
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
