"""Adaptador Outbox del puerto EventPublisher (Transactional Outbox, ADR-026).

En lugar de enviar el evento a RabbitMQ, lo REGISTRA como una fila de
`outbox_events` en la MISMA sesión de SQLAlchemy que usa el repositorio de
itinerarios. Así el itinerario y su evento quedan en una sola transacción:
el commit del caso de uso guarda los dos o ninguno.

Este adaptador no hace commit: lo decide el caso de uso mediante UnitOfWork.
Un error de base de datos aparece al hacer commit y deshace todo (rollback).
El Outbox Relay (entrega 5B) publica después los eventos pendientes.
"""

import logging

from sqlalchemy.orm import Session

from app.application.events import ItineraryCreatedEvent
from app.application.outbox import OutboxMessage
from app.application.ports import EventPublisher
from app.infrastructure.persistence.models import OutboxEventORM

logger = logging.getLogger(__name__)


class OutboxEventPublisher(EventPublisher):
    """Registra el evento en `outbox_events` dentro de la transacción actual."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def publish(self, event: ItineraryCreatedEvent) -> None:
        message = OutboxMessage.from_event(event)
        self._session.add(_to_orm(message))
        logger.debug(
            "Evento %s (event_id=%s) agregado a la outbox; se confirma con el commit",
            message.event_type,
            message.id,
        )


def _to_orm(message: OutboxMessage) -> OutboxEventORM:
    return OutboxEventORM(
        id=message.id,
        aggregate_type=message.aggregate_type,
        aggregate_id=message.aggregate_id,
        event_type=message.event_type,
        event_version=message.event_version,
        payload=message.payload,
        occurred_at=message.occurred_at,
        published_at=message.published_at,
        attempts=message.attempts,
        last_error=message.last_error,
        failed_at=message.failed_at,
    )
