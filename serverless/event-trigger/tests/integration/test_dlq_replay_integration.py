"""Integración del reprocesamiento de la DLQ con RabbitMQ real (SKIPPED sin RabbitMQ).

Usa una topología de prueba propia (ver conftest.py): no toca la DLQ ni la cola reales.
"""

import json

from app.infrastructure.rabbitmq.dlq_replayer import DeadLetterReplayer
from tests.fakes import REJECTED, SUCCESS, ScriptedInvoker
from tests.integration.conftest import message_count, publish, run_trigger


def send_to_dlq(channel, topology, count: int) -> list[str]:
    """Publica `count` mensajes y hace que el trigger los rechace: terminan en la DLQ de prueba."""
    ids = [
        publish(channel, topology, json.dumps({"event_id": f"evento-{n}"}).encode(), f"evento-{n}")
        for n in range(count)
    ]
    run_trigger(ScriptedInvoker(REJECTED), topology, max_messages=count)
    assert message_count(channel, topology.dead_letter_queue, count) == count
    return ids


def test_mueve_un_mensaje_de_la_dlq_a_la_cola(rabbitmq_channel, test_topology):
    ids = send_to_dlq(rabbitmq_channel, test_topology, 2)

    moved = DeadLetterReplayer(rabbitmq_channel, test_topology).replay(limit=1)

    assert [m.message_id for m in moved] == [ids[0]]
    assert moved[0].death_reason == "rejected"
    assert message_count(rabbitmq_channel, test_topology.queue, 1) == 1
    assert message_count(rabbitmq_channel, test_topology.dead_letter_queue, 1) == 1


def test_mueve_todos_y_el_trigger_los_procesa_cuando_el_problema_se_corrigio(rabbitmq_channel, test_topology):
    send_to_dlq(rabbitmq_channel, test_topology, 3)

    moved = DeadLetterReplayer(rabbitmq_channel, test_topology).replay(limit=None)

    assert len(moved) == 3
    assert message_count(rabbitmq_channel, test_topology.dead_letter_queue, 0) == 0
    # Con la función corregida, el trigger los procesa (ACK) y no vuelven a la DLQ
    assert run_trigger(ScriptedInvoker(SUCCESS), test_topology, max_messages=3) == 3
    assert message_count(rabbitmq_channel, test_topology.queue, 0) == 0
    assert message_count(rabbitmq_channel, test_topology.dead_letter_queue, 0) == 0


def test_el_mensaje_devuelto_no_lleva_el_x_death_anterior(rabbitmq_channel, test_topology):
    send_to_dlq(rabbitmq_channel, test_topology, 1)

    DeadLetterReplayer(rabbitmq_channel, test_topology).replay()

    method, properties, body = rabbitmq_channel.basic_get(test_topology.queue, auto_ack=True)
    assert properties.message_id == "evento-0"
    assert "x-death" not in (properties.headers or {})
    assert properties.headers["x-dlq-replays"] == 1
    assert json.loads(body) == {"event_id": "evento-0"}


def test_si_el_problema_sigue_vuelve_a_la_dlq_sin_ciclo_infinito(rabbitmq_channel, test_topology):
    send_to_dlq(rabbitmq_channel, test_topology, 1)

    moved = DeadLetterReplayer(rabbitmq_channel, test_topology).replay(limit=None)
    run_trigger(ScriptedInvoker(REJECTED), test_topology)

    assert len(moved) == 1  # solo los que había al empezar
    assert message_count(rabbitmq_channel, test_topology.dead_letter_queue, 1) == 1
