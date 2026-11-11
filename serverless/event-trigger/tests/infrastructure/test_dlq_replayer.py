"""Pruebas del reprocesamiento de la DLQ con un canal falso (sin RabbitMQ)."""

from types import SimpleNamespace

import pika
import pytest
from pika.exceptions import UnroutableError

from app.infrastructure.rabbitmq.dlq_replayer import DeadLetterReplayer, DlqReplayError
from app.infrastructure.rabbitmq.topology import NOTIFICATION_TOPOLOGY
from app.replay_dlq import parse_args


def dead_letter(tag: int, message_id: str, headers: dict | None = None):
    """Un mensaje como lo entrega basic_get desde la DLQ (con el header x-death de RabbitMQ)."""
    base_headers = {
        "x-death": [{"queue": "notification.itinerary-created", "reason": "rejected", "count": 1}],
        "x-first-death-reason": "rejected",
        "x-first-death-queue": "notification.itinerary-created",
        "x-last-death-reason": "rejected",
        "event_version": 1,
    }
    base_headers.update(headers or {})
    properties = pika.BasicProperties(
        message_id=message_id,
        correlation_id="cid-1",
        content_type="application/json",
        delivery_mode=2,
        type="itinerary.created",
        headers=base_headers,
    )
    return SimpleNamespace(delivery_tag=tag), properties, f'{{"event_id": "{message_id}"}}'.encode()


class FakeChannel:
    def __init__(self, messages: list, publish_error: Exception | None = None) -> None:
        self._messages = list(messages)
        self._publish_error = publish_error
        self.calls: list[tuple[str, dict]] = []

    def confirm_delivery(self) -> None:
        self.calls.append(("confirm_delivery", {}))

    def queue_declare(self, queue: str, passive: bool):
        return SimpleNamespace(method=SimpleNamespace(message_count=len(self._messages)))

    def basic_get(self, queue: str, auto_ack: bool):
        self.calls.append(("basic_get", {"queue": queue, "auto_ack": auto_ack}))
        if not self._messages:
            return None, None, None
        return self._messages.pop(0)

    def basic_publish(self, **kwargs) -> None:
        self.calls.append(("basic_publish", kwargs))
        if self._publish_error is not None:
            raise self._publish_error

    def basic_ack(self, delivery_tag: int) -> None:
        self.calls.append(("basic_ack", {"delivery_tag": delivery_tag}))

    def basic_nack(self, delivery_tag: int, requeue: bool) -> None:
        self.calls.append(("basic_nack", {"delivery_tag": delivery_tag, "requeue": requeue}))

    def published(self) -> list[dict]:
        return [kwargs for name, kwargs in self.calls if name == "basic_publish"]


def test_por_defecto_mueve_un_solo_mensaje():
    channel = FakeChannel([dead_letter(1, "m-1"), dead_letter(2, "m-2")])

    moved = DeadLetterReplayer(channel).replay()

    assert [m.message_id for m in moved] == ["m-1"]
    assert len(channel.published()) == 1
    assert ("basic_ack", {"delivery_tag": 1}) in channel.calls


def test_con_limit_none_mueve_todos_los_que_habia():
    channel = FakeChannel([dead_letter(1, "m-1"), dead_letter(2, "m-2"), dead_letter(3, "m-3")])

    moved = DeadLetterReplayer(channel).replay(limit=None)

    assert [m.message_id for m in moved] == ["m-1", "m-2", "m-3"]


def test_con_la_dlq_vacia_no_hace_nada():
    channel = FakeChannel([])

    assert DeadLetterReplayer(channel).replay(limit=None) == []
    assert channel.published() == []


def test_publica_directo_en_la_cola_principal_con_confirmacion():
    """Exchange por defecto + routing key = nombre de la cola: llega solo a esa cola."""
    channel = FakeChannel([dead_letter(1, "m-1")])

    DeadLetterReplayer(channel).replay()

    assert channel.calls[0] == ("confirm_delivery", {})
    publish = channel.published()[0]
    assert publish["exchange"] == ""
    assert publish["routing_key"] == NOTIFICATION_TOPOLOGY.queue
    assert publish["mandatory"] is True
    assert publish["body"] == b'{"event_id": "m-1"}'


def test_confirma_en_la_dlq_solo_despues_de_publicar():
    channel = FakeChannel([dead_letter(1, "m-1")])

    DeadLetterReplayer(channel).replay()

    names = [name for name, _ in channel.calls]
    assert names.index("basic_publish") < names.index("basic_ack")


def test_conserva_las_propiedades_y_quita_los_headers_del_rechazo():
    channel = FakeChannel([dead_letter(1, "m-1")])

    DeadLetterReplayer(channel).replay()

    properties: pika.BasicProperties = channel.published()[0]["properties"]
    assert properties.message_id == "m-1"
    assert properties.correlation_id == "cid-1"
    assert properties.delivery_mode == 2
    assert properties.content_type == "application/json"
    assert properties.headers == {"event_version": 1, "x-dlq-replays": 1}


def test_cuenta_las_veces_que_se_reproceso_y_el_motivo_anterior():
    channel = FakeChannel([dead_letter(1, "m-1", headers={"x-dlq-replays": 2})])

    moved = DeadLetterReplayer(channel).replay()

    assert moved[0].replays == 3
    assert moved[0].death_reason == "rejected"
    assert moved[0].death_count == 1
    assert channel.published()[0]["properties"].headers["x-dlq-replays"] == 3


def test_si_rabbitmq_no_acepta_el_mensaje_vuelve_a_la_dlq():
    channel = FakeChannel([dead_letter(1, "m-1")], publish_error=UnroutableError([]))
    replayer = DeadLetterReplayer(channel)

    with pytest.raises(DlqReplayError):
        replayer.replay()

    assert ("basic_nack", {"delivery_tag": 1, "requeue": True}) in channel.calls
    assert ("basic_ack", {"delivery_tag": 1}) not in channel.calls


def test_el_comando_mueve_uno_por_defecto_y_todos_con_all():
    assert parse_args([]).all is False
    assert parse_args(["--all"]).all is True
