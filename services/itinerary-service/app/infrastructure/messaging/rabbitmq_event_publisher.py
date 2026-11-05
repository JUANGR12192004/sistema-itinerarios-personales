"""Adaptador que implementa el puerto EventPublisher publicando en RabbitMQ con pika (ADR-021).

Cada publicación:
1. Abre una conexión (BlockingConnection no es segura entre hilos y FastAPI ejecuta
   las rutas `def` en varios hilos; una conexión por publicación evita compartirla).
2. Activa los publisher confirms: RabbitMQ confirma que recibió y enrutó el mensaje.
3. Declara la topología (idempotente).
4. Publica el evento como JSON persistente, con `mandatory=True`: si ninguna cola
   lo recibe, RabbitMQ lo devuelve y la publicación falla en lugar de perderse en silencio.
5. Cierra la conexión, haya error o no.

Cualquier error técnico de pika se envuelve en EventPublishError: el caso de uso
no conoce pika (regla de dependencias de la arquitectura hexagonal).
"""

import json
import logging
from collections.abc import Callable

import pika
from pika.adapters.blocking_connection import BlockingConnection
from pika.exceptions import AMQPError

from app.application.events import ItineraryCreatedEvent
from app.application.exceptions import EventPublishError
from app.application.ports import EventPublisher
from app.infrastructure.messaging.topology import (
    EXCHANGE,
    ROUTING_KEY_ITINERARY_CREATED,
    declare_topology,
)

logger = logging.getLogger(__name__)

ConnectionFactory = Callable[[pika.ConnectionParameters], BlockingConnection]

PERSISTENT_DELIVERY_MODE = 2  # el mensaje se guarda en disco y sobrevive a un reinicio


class RabbitMQEventPublisher(EventPublisher):
    """Publica ItineraryCreatedEvent en el exchange `itinerary.events`.

    `connection_factory` permite inyectar una conexión falsa en las pruebas
    (por defecto se usa la BlockingConnection real de pika).
    """

    def __init__(
        self,
        url: str,
        timeout_seconds: float,
        connection_factory: ConnectionFactory = pika.BlockingConnection,
    ) -> None:
        self._parameters = pika.URLParameters(url)
        # Sin estos valores, un RabbitMQ caído podría bloquear la solicitud HTTP mucho tiempo
        self._parameters.socket_timeout = timeout_seconds
        self._parameters.stack_timeout = timeout_seconds
        self._parameters.blocked_connection_timeout = timeout_seconds
        self._parameters.connection_attempts = 1
        self._connection_factory = connection_factory

    def publish(self, event: ItineraryCreatedEvent) -> None:
        try:
            connection = self._connection_factory(self._parameters)
        except (AMQPError, OSError) as exc:
            raise EventPublishError(
                f"No se pudo conectar con RabbitMQ en {self._parameters.host}:{self._parameters.port}"
            ) from exc

        try:
            channel = connection.channel()
            channel.confirm_delivery()
            declare_topology(channel)
            channel.basic_publish(
                exchange=EXCHANGE,
                routing_key=ROUTING_KEY_ITINERARY_CREATED,
                body=json.dumps(event.to_dict(), ensure_ascii=False).encode("utf-8"),
                properties=_message_properties(event),
                mandatory=True,
            )
        except (AMQPError, OSError) as exc:
            # Incluye UnroutableError (ninguna cola lo recibió) y NackError (RabbitMQ lo rechazó)
            raise EventPublishError(
                f"RabbitMQ no aceptó el evento {event.event_id}: {type(exc).__name__}"
            ) from exc
        finally:
            _close_quietly(connection)

        logger.info(
            "Evento publicado: %s event_id=%s itinerary_id=%s correlation_id=%s",
            event.EVENT_TYPE,
            event.event_id,
            event.itinerary_id,
            event.correlation_id,
        )


def _message_properties(event: ItineraryCreatedEvent) -> pika.BasicProperties:
    """Propiedades AMQP del mensaje: metadatos que el consumidor puede leer sin abrir el JSON."""
    return pika.BasicProperties(
        content_type="application/json",
        content_encoding="utf-8",
        delivery_mode=PERSISTENT_DELIVERY_MODE,
        message_id=str(event.event_id),  # clave de idempotencia para el consumidor
        correlation_id=event.correlation_id,
        type=event.EVENT_TYPE,
        app_id=event.PRODUCER,
        timestamp=int(event.occurred_at.timestamp()),
        headers={"event_version": event.EVENT_VERSION},
    )


def _close_quietly(connection: BlockingConnection) -> None:
    """Cierra la conexión sin ocultar el error original de la publicación."""
    try:
        if connection.is_open:
            connection.close()
    except (AMQPError, OSError):
        logger.warning("No se pudo cerrar la conexión con RabbitMQ", exc_info=True)
