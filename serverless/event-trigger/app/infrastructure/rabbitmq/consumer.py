"""Consumidor de RabbitMQ del Event Trigger (ADR-031), con pika.

Cada vez que se conecta:
1. Declara la topología del consumidor (ADR-032).
2. Fija `prefetch_count=1`: RabbitMQ le entrega un solo mensaje a la vez y no envía el
   siguiente hasta recibir la respuesta (ACK, reject o nack) del actual.
3. Consume con ACK manual: por cada mensaje, DeliveryHandler decide y aquí se aplica.

Si el trigger se cae antes de responder, RabbitMQ vuelve a entregar el mensaje: entrega
"al menos una vez". La función es idempotente (ADR-030), así que no hay notificaciones dobles.

Se usa `channel.consume(..., inactivity_timeout=1)`, que devuelve el control cada segundo
aunque no lleguen mensajes. Así Ctrl+C se atiende enseguida en Windows y las pruebas pueden
parar cuando la cola queda vacía.
"""

import logging
from collections.abc import Callable

import pika
from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection
from pika.exceptions import AMQPError

from app.application.delivery_handler import Decision, DeliveryHandler
from app.infrastructure.rabbitmq.topology import NOTIFICATION_TOPOLOGY, QueueTopology, declare_topology

logger = logging.getLogger(__name__)

ConnectionFactory = Callable[[pika.ConnectionParameters], BlockingConnection]
# Crea el DeliveryHandler con la función de espera de la conexión (connection.sleep)
HandlerFactory = Callable[[Callable[[float], None]], DeliveryHandler]

PREFETCH_COUNT = 1
INACTIVITY_TIMEOUT_SECONDS = 1.0


def apply_decision(channel: BlockingChannel, delivery_tag: int, decision: Decision) -> None:
    """Responde a RabbitMQ según la decisión de la política."""
    if decision is Decision.ACK:
        channel.basic_ack(delivery_tag=delivery_tag)
    elif decision is Decision.REJECT:
        # Sin reencolar: RabbitMQ lo envía al dead letter exchange y de ahí a la DLQ
        channel.basic_reject(delivery_tag=delivery_tag, requeue=False)
    else:
        # Vuelve a la cola (al inicio) para intentarlo de nuevo; nunca a la DLQ
        channel.basic_nack(delivery_tag=delivery_tag, requeue=True)


class RabbitMQConsumer:
    """Conecta con RabbitMQ y procesa la cola notification.itinerary-created."""

    def __init__(
        self,
        url: str,
        timeout_seconds: float,
        handler_factory: HandlerFactory,
        connection_factory: ConnectionFactory = pika.BlockingConnection,
        topology: QueueTopology = NOTIFICATION_TOPOLOGY,
    ) -> None:
        self._parameters = pika.URLParameters(url)
        self._parameters.socket_timeout = timeout_seconds
        self._parameters.stack_timeout = timeout_seconds
        self._parameters.connection_attempts = 1
        self._handler_factory = handler_factory
        self._connection_factory = connection_factory
        self._topology = topology

    def run(self, max_messages: int | None = None, stop_when_idle: bool = False) -> int:
        """Consume hasta que se pierda la conexión (lanza AMQPError) o se pulse Ctrl+C.

        `max_messages` y `stop_when_idle` sirven para las pruebas: paran tras N mensajes o
        cuando la cola queda vacía. Devuelve cuántos mensajes se procesaron.
        """
        connection = self._connection_factory(self._parameters)
        processed = 0
        try:
            channel = connection.channel()
            declare_topology(channel, self._topology)
            channel.basic_qos(prefetch_count=PREFETCH_COUNT)
            handler = self._handler_factory(connection.sleep)
            logger.info(
                "Event Trigger conectado a %s:%s; escuchando la cola %s",
                self._parameters.host,
                self._parameters.port,
                self._topology.queue,
            )

            for method, properties, body in channel.consume(
                self._topology.queue, auto_ack=False, inactivity_timeout=INACTIVITY_TIMEOUT_SECONDS
            ):
                if method is None:  # pasó un segundo sin mensajes
                    if stop_when_idle:
                        break
                    continue

                if method.redelivered:
                    logger.info("Mensaje entregado de nuevo: message_id=%s", properties.message_id)
                decision = handler.handle(body, properties.message_id)
                apply_decision(channel, method.delivery_tag, decision)
                processed += 1
                if max_messages is not None and processed >= max_messages:
                    break

            channel.cancel()
            return processed
        finally:
            _close_quietly(connection)


def _close_quietly(connection: BlockingConnection) -> None:
    """Cierra la conexión. Un mensaje sin responder vuelve a la cola al cerrarse la conexión."""
    try:
        if connection.is_open:
            connection.close()
    except (AMQPError, OSError):
        logger.debug("La conexión con RabbitMQ ya estaba cerrada", exc_info=True)
