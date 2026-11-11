"""Integración del trigger con un RabbitMQ real y una función falsa (SKIPPED sin RabbitMQ).

Comprueba que cada decisión de la política llega a la cola correcta:
ACK → se borra; REJECT → DLQ; REQUEUE → vuelve a la cola principal (nunca a la DLQ).
Usa una topología de prueba propia (ver conftest.py): no toca las colas reales.
"""

import json

import pytest
from pika.exceptions import ChannelClosedByBroker

from app.infrastructure.rabbitmq.topology import NOTIFICATION_TOPOLOGY, declare_topology
from tests.fakes import FUNCTION_ERROR, INFRASTRUCTURE_ERROR, REJECTED, SUCCESS, ScriptedInvoker
from tests.integration.conftest import message_count, publish, run_trigger

EVENT = json.dumps({"event_id": "7d9f1c2e-4b5a-4e8f-9a1b-2c3d4e5f6a7b"}).encode()


def test_la_topologia_real_es_compatible_con_la_que_ya_existe(rabbitmq_channel):
    """Declarar la topología real con los argumentos de ADR-021 no causa PRECONDITION_FAILED.

    Solo se comprueba si la cola real ya existe: si no existe, declararla la crearía y cambiaría
    el sistema (por ejemplo, el escenario "trigger apagado desde el principio" de la demostración).
    Redeclarar algo que existe con los mismos argumentos no cambia sus mensajes.
    """
    probe = rabbitmq_channel.connection.channel()
    try:
        probe.queue_declare(queue=NOTIFICATION_TOPOLOGY.queue, passive=True)
    except ChannelClosedByBroker:
        pytest.skip("La cola real no existe; no se crea para no alterar el sistema")
    probe.close()

    declare_topology(rabbitmq_channel, NOTIFICATION_TOPOLOGY)

    assert rabbitmq_channel.is_open


def test_exito_borra_el_mensaje_de_la_cola(rabbitmq_channel, test_topology):
    publish(rabbitmq_channel, test_topology, EVENT)
    invoker = ScriptedInvoker(SUCCESS)

    assert run_trigger(invoker, test_topology) == 1

    assert len(invoker.calls) == 1
    assert message_count(rabbitmq_channel, test_topology.queue, 0) == 0
    assert message_count(rabbitmq_channel, test_topology.dead_letter_queue, 0) == 0


def test_evento_rechazado_va_a_la_dlq(rabbitmq_channel, test_topology):
    message_id = publish(rabbitmq_channel, test_topology, EVENT)

    run_trigger(ScriptedInvoker(REJECTED), test_topology)

    assert message_count(rabbitmq_channel, test_topology.queue, 0) == 0
    assert message_count(rabbitmq_channel, test_topology.dead_letter_queue, 1) == 1
    method, properties, _ = rabbitmq_channel.basic_get(test_topology.dead_letter_queue, auto_ack=True)
    assert properties.message_id == message_id
    # RabbitMQ anota en el header x-death de dónde viene y por qué
    death = properties.headers["x-death"][0]
    assert death["queue"] == test_topology.queue
    assert death["reason"] == "rejected"


def test_mensaje_que_no_es_json_va_a_la_dlq_sin_invocar_la_funcion(rabbitmq_channel, test_topology):
    publish(rabbitmq_channel, test_topology, b"esto no es JSON")
    invoker = ScriptedInvoker(SUCCESS)

    run_trigger(invoker, test_topology)

    assert invoker.calls == []
    assert message_count(rabbitmq_channel, test_topology.dead_letter_queue, 1) == 1


def test_fallo_de_infraestructura_devuelve_el_mensaje_a_la_cola_y_no_a_la_dlq(rabbitmq_channel, test_topology):
    publish(rabbitmq_channel, test_topology, EVENT)

    run_trigger(ScriptedInvoker(INFRASTRUCTURE_ERROR), test_topology, max_messages=1)

    assert message_count(rabbitmq_channel, test_topology.queue, 1) == 1
    assert message_count(rabbitmq_channel, test_topology.dead_letter_queue, 0) == 0


def test_el_mensaje_devuelto_se_procesa_cuando_vuelve_la_funcion(rabbitmq_channel, test_topology):
    publish(rabbitmq_channel, test_topology, EVENT)
    run_trigger(ScriptedInvoker(INFRASTRUCTURE_ERROR), test_topology, max_messages=1)

    run_trigger(ScriptedInvoker(SUCCESS), test_topology)

    assert message_count(rabbitmq_channel, test_topology.queue, 0) == 0
    assert message_count(rabbitmq_channel, test_topology.dead_letter_queue, 0) == 0


def test_error_de_la_funcion_persistente_va_a_la_dlq(rabbitmq_channel, test_topology):
    publish(rabbitmq_channel, test_topology, EVENT)
    invoker = ScriptedInvoker(FUNCTION_ERROR)

    run_trigger(invoker, test_topology)

    assert len(invoker.calls) == 2  # FAST_POLICY: 2 intentos
    assert message_count(rabbitmq_channel, test_topology.queue, 0) == 0
    assert message_count(rabbitmq_channel, test_topology.dead_letter_queue, 1) == 1
