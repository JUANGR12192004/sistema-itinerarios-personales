"""Mensaje pendiente de la outbox (Transactional Outbox, Fase 5, ADR-024).

Un `OutboxMessage` es un evento de integración ya registrado en la base de datos
del servicio y que todavía puede estar pendiente de publicar en RabbitMQ.

Vive en la capa de aplicación (no en el dominio): es un mecanismo técnico para
entregar eventos de forma confiable, no una regla del negocio de itinerarios.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.application.events import ItineraryCreatedEvent

# Tipo de agregado que origina los eventos de este servicio
AGGREGATE_TYPE_ITINERARY = "itinerary"


@dataclass
class OutboxMessage:
    """Fila de la tabla `outbox_events`, vista desde la aplicación.

    - `id` es el mismo `event_id` del evento: una fila por evento.
    - `payload` es el evento completo con la forma exacta del contrato (ADR-020).
    - `published_at` es None mientras el evento está pendiente.
    - `attempts` y `last_error` registran los intentos fallidos del relay (Fase 5B).
    - `failed_at` marca un fallo PERMANENTE (mensaje venenoso, ADR-027): el mensaje
      deja de estar pendiente y no se reintenta.
    """

    id: UUID
    aggregate_type: str
    aggregate_id: UUID
    event_type: str
    event_version: int
    payload: dict[str, Any]
    occurred_at: datetime
    published_at: datetime | None = None
    attempts: int = 0
    last_error: str | None = None
    failed_at: datetime | None = None

    @classmethod
    def from_event(cls, event: ItineraryCreatedEvent) -> OutboxMessage:
        """Crea el mensaje pendiente a partir del evento de integración."""
        return cls(
            id=event.event_id,
            aggregate_type=AGGREGATE_TYPE_ITINERARY,
            aggregate_id=event.itinerary_id,
            event_type=event.EVENT_TYPE,
            event_version=event.EVENT_VERSION,
            payload=event.to_dict(),
            occurred_at=event.occurred_at,
        )
