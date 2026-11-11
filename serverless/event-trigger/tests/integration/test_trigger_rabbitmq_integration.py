"""Integración del trigger con un RabbitMQ real y una función falsa (SKIPPED sin RabbitMQ).

Comprueba que cada decisión de la política llega a la cola correcta:
ACK → se borra; REJECT → DLQ; REQUEUE → vuelve a la cola principal (nunca a la DLQ).
"""

import json

from app.infrastructure.rabbitmq.topology import (
    DEAD_LETTER_EXCHANGE,
    DEAD_LETTER_QUEUE,
    QUEUE_NOTIFICATIONS,
    declare_topology,
)
from tests.fakes import FUNCTION_ERROR, INFRASTRUCTURE_ERROR, REJECTED, SUCCESS, ScriptedInvoker
from tests.integration.conftest import message_count, publish, run_trigger

EVENT = json.dumps({"event_id": "7d9f1c2e-4b5a-4e8f-9a1b-2c3d4e5f6a7b"}).encode()


def test_la_topologia_es_compatible_con_la_que_ya_existe(rabbitmq_channel):
    """Declarar otra vez con los mismos argumentos de ADR-021 no causa PRECONDITION_FAILED."""
    declare_topology(rabbitmq_channel)
    rabbitmq_channel.queue_declare(
        queue=QUEUE_NOTIFICATIONS,
        durable=True,
        arguments={"x-dead-letter-exchange": DEAD_LETTER_EXCHANGE},
    )

    assert rabbitmq_channel.is_open


def test_exito_borra_el_mensaje_de_la_cola(rabbitmq_channel):
    publish(rabbitmq_channel, EVENT)
    invoker = ScriptedInvoker(SUCCESS)

    assert run_trigger(invoker) == 1

    assert len(invoker.calls) == 1
    assert message_count(rabbitmq_channel, QUEUE_NOTIFICATIONS, 0) == 0
    assert message_count(rabbitmq_channel, DEAD_LETTER_QUEUE, 0) == 0


def test_evento_rechazado_va_a_la_dlq(rabbitmq_channel):
    message_id = publish(rabbitmq_channel, EVENT)

    run_trigger(ScriptedInvoker(REJECTED))

    assert message_count(rabbitmq_channel, QUEUE_NOTIFICATIONS, 0) == 0
    assert message_count(rabbitmq_channel, DEAD_LETTER_QUEUE, 1) == 1
    method, properties, _ = rabbitmq_channel.basic_get(DEAD_LETTER_QUEUE, auto_ack=True)
    assert properties.message_id == message_id
    # RabbitMQ anota en el header x-death de dónde viene y por qué
    death = properties.headers["x-death"][0]
    assert death["queue"] == QUEUE_NOTIFICATIONS
    assert death["reason"] == "rejected"


def test_mensaje_que_no_es_json_va_a_la_dlq_sin_invocar_la_funcion(rabbitmq_channel):
    publish(rabbitmq_channel, b"esto no es JSON")
    invoker = ScriptedInvoker(SUCCESS)

    run_trigger(invoker)

    assert invoker.calls == []
    assert message_count(rabbitmq_channel, DEAD_LETTER_QUEUE, 1) == 1


def test_fallo_de_infraestructura_devuelve_el_mensaje_a_la_cola_y_no_a_la_dlq(rabbitmq_channel):
    publish(rabbitmq_channel, EVENT)

    run_trigger(ScriptedInvoker(INFRASTRUCTURE_ERROR), max_messages=1)

    assert message_count(rabbitmq_channel, QUEUE_NOTIFICATIONS, 1) == 1
    assert message_count(rabbitmq_channel, DEAD_LETTER_QUEUE, 0) == 0


def test_el_mensaje_devuelto_se_procesa_cuando_vuelve_la_funcion(rabbitmq_channel):
    publish(rabbitmq_channel, EVENT)
    run_trigger(ScriptedInvoker(INFRASTRUCTURE_ERROR), max_messages=1)

    run_trigger(ScriptedInvoker(SUCCESS))

    assert message_count(rabbitmq_channel, QUEUE_NOTIFICATIONS, 0) == 0
    assert message_count(rabbitmq_channel, DEAD_LETTER_QUEUE, 0) == 0


def test_error_de_la_funcion_persistente_va_a_la_dlq(rabbitmq_channel):
    publish(rabbitmq_channel, EVENT)
    invoker = ScriptedInvoker(FUNCTION_ERROR)

    run_trigger(invoker)

    assert len(invoker.calls) == 2  # FAST_POLICY: 2 intentos
    assert message_count(rabbitmq_channel, QUEUE_NOTIFICATIONS, 0) == 0
    assert message_count(rabbitmq_channel, DEAD_LETTER_QUEUE, 1) == 1
