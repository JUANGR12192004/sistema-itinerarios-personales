"""Reprocesamiento de la DLQ: devuelve mensajes de la cola de fallidos a la cola principal (ADR-031).

Un mensaje válido puede terminar en la DLQ por un problema de despliegue: por ejemplo, la
migración del historial sin aplicar, o una imagen de la función con un error que el RIE
informa con un errorType distinto de TransientError. Corregido el problema, este adaptador
los devuelve a la cola para que el trigger los procese otra vez.

Por cada mensaje, de uno en uno:
1. Lo toma de la DLQ sin confirmarlo (basic_get con ACK manual).
2. Lo publica directamente en la cola principal: exchange por defecto ("") con la routing key
   igual al nombre de la cola. Así llega SOLO a la cola de notificaciones, aunque mañana haya
   otros consumidores enlazados al exchange itinerary.events.
3. Espera la confirmación de RabbitMQ (publisher confirms, mandatory=True).
4. Recién entonces lo confirma (ACK) en la DLQ, que lo borra de ahí.

Si el paso 2 o 3 falla, el mensaje se devuelve a la DLQ (nack con requeue): no se pierde.
Si el proceso se cae entre 3 y 4, el mensaje queda en las dos colas: la función es
idempotente (ADR-030), así que la segunda copia responde ALREADY_PROCESSED.

Solo se mueven los mensajes que había al empezar: si el problema sigue sin resolverse y el
trigger los vuelve a rechazar enseguida, no se crea un ciclo sin fin.
"""

import logging
from dataclasses import dataclass
from typing import Any

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPError

from app.infrastructure.rabbitmq.topology import NOTIFICATION_TOPOLOGY, QueueTopology

logger = logging.getLogger(__name__)

DEFAULT_EXCHANGE = ""
# Headers que RabbitMQ agrega al enviar un mensaje a la DLQ. Se quitan al devolverlo:
# describen el rechazo anterior, no el mensaje.
DEATH_HEADER_PREFIXES = ("x-death", "x-first-death", "x-last-death")
REPLAY_COUNT_HEADER = "x-dlq-replays"


class DlqReplayError(Exception):
    """RabbitMQ no aceptó el mensaje en la cola principal; el mensaje sigue en la DLQ."""


@dataclass(frozen=True)
class ReplayedMessage:
    """Un mensaje devuelto a la cola, con el motivo de su último rechazo (para el registro)."""

    message_id: str | None
    death_reason: str | None
    death_count: int
    replays: int


class DeadLetterReplayer:
    """Mueve mensajes de la DLQ a la cola principal, uno por uno."""

    def __init__(self, channel: BlockingChannel, topology: QueueTopology = NOTIFICATION_TOPOLOGY) -> None:
        self._channel = channel
        self._topology = topology

    def pending(self) -> int:
        """Cantidad de mensajes que hay ahora en la DLQ."""
        return self._channel.queue_declare(queue=self._topology.dead_letter_queue, passive=True).method.message_count

    def replay(self, limit: int | None = 1) -> list[ReplayedMessage]:
        """Devuelve hasta `limit` mensajes (todos los que había al empezar si es None)."""
        self._channel.confirm_delivery()
        available = self.pending()
        to_move = available if limit is None else min(limit, available)

        moved: list[ReplayedMessage] = []
        for _ in range(to_move):
            method, properties, body = self._channel.basic_get(self._topology.dead_letter_queue, auto_ack=False)
            if method is None:  # alguien más vació la DLQ mientras tanto
                break
            replayed = self._move(method.delivery_tag, properties, body)
            moved.append(replayed)
            logger.info(
                "Mensaje devuelto de la DLQ a la cola %s: message_id=%s motivo del rechazo=%s "
                "veces rechazado=%d reprocesos=%d",
                self._topology.queue,
                replayed.message_id,
                replayed.death_reason,
                replayed.death_count,
                replayed.replays,
            )
        return moved

    def _move(self, delivery_tag: int, properties: pika.BasicProperties, body: bytes) -> ReplayedMessage:
        headers = dict(properties.headers or {})
        death = (headers.get("x-death") or [{}])[0]
        replays = int(headers.get(REPLAY_COUNT_HEADER, 0)) + 1
        try:
            self._channel.basic_publish(
                exchange=DEFAULT_EXCHANGE,
                routing_key=self._topology.queue,
                body=body,
                properties=_replay_properties(properties, headers, replays),
                mandatory=True,
            )
        except AMQPError as exc:
            self._channel.basic_nack(delivery_tag=delivery_tag, requeue=True)
            raise DlqReplayError(
                f"RabbitMQ no aceptó el mensaje {properties.message_id} en {self._topology.queue}: "
                f"{type(exc).__name__}. Sigue en la DLQ"
            ) from exc

        self._channel.basic_ack(delivery_tag=delivery_tag)
        return ReplayedMessage(
            message_id=properties.message_id,
            death_reason=_as_text(death.get("reason")),
            death_count=int(death.get("count", 0)),
            replays=replays,
        )


def _replay_properties(
    properties: pika.BasicProperties, headers: dict[str, Any], replays: int
) -> pika.BasicProperties:
    """Copia las propiedades del mensaje sin los headers del rechazo anterior."""
    clean_headers = {
        key: value for key, value in headers.items() if not key.startswith(DEATH_HEADER_PREFIXES)
    }
    clean_headers[REPLAY_COUNT_HEADER] = replays
    return pika.BasicProperties(
        content_type=properties.content_type,
        content_encoding=properties.content_encoding,
        delivery_mode=properties.delivery_mode or 2,
        message_id=properties.message_id,
        correlation_id=properties.correlation_id,
        type=properties.type,
        app_id=properties.app_id,
        timestamp=properties.timestamp,
        headers=clean_headers,
    )


def _as_text(value: Any) -> str | None:
    """pika entrega algunos valores de los headers como bytes."""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value
