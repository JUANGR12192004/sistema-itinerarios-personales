"""Caso de uso de SendNotificationFunction: notificar la creación de un itinerario (ADR-030).

Orden de los pasos, dentro de una sola transacción:

1. Construir el NotificationRecord (la regla del destinatario está en el dominio).
2. Registrarlo solo si su event_id no existe: si ya existía, el evento es un duplicado
   (entrega "al menos una vez") y se responde ALREADY_PROCESSED sin volver a enviar.
3. Enviar la notificación, solo si hay destinatario.
4. Confirmar (commit).

Se registra ANTES de enviar: la restricción única de event_id "reserva" el evento, así
dos copias que llegan a la vez no envían dos notificaciones. Si el envío falla, no hay
commit, la transacción se deshace y el evento se puede reintentar.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID

from app.application.events import ItineraryCreatedEvent
from app.application.ports import NotificationHistoryRepository, NotificationSender, UnitOfWork
from app.domain.notification_record import NotificationRecord, NotificationStatus

logger = logging.getLogger(__name__)


class ProcessingStatus(StrEnum):
    """Resultado de una invocación de la función: el campo `status` de su respuesta (ADR-028)."""

    PROCESSED = "PROCESSED"
    ALREADY_PROCESSED = "ALREADY_PROCESSED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class NotificationResult:
    """Lo que devuelve el caso de uso. Los campos de la notificación son None si era un duplicado."""

    status: ProcessingStatus
    event_id: UUID
    notification_id: UUID | None = None
    notification_status: NotificationStatus | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_message(event: ItineraryCreatedEvent) -> str:
    """Texto de la notificación. Usa los ids de los aeropuertos: la función no consulta
    Airport Service, para no depender de otro servicio (solo conoce el evento)."""
    return (
        f"Hola {event.traveler_name}: tu itinerario {event.itinerary_id} quedó registrado. "
        f"Salida desde el aeropuerto {event.departure_airport_id} hacia el aeropuerto "
        f"{event.arrival_airport_id} el {event.travel_date.isoformat()}, "
        f"con una duración estimada de {event.duration_minutes} minutos."
    )


class NotifyItineraryCreatedUseCase:
    """Procesa un ItineraryCreatedEvent: registra la notificación y la envía una sola vez."""

    def __init__(
        self,
        history: NotificationHistoryRepository,
        sender: NotificationSender,
        unit_of_work: UnitOfWork,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._history = history
        self._sender = sender
        self._unit_of_work = unit_of_work
        self._clock = clock

    def execute(self, event: ItineraryCreatedEvent) -> NotificationResult:
        record = NotificationRecord.create(
            event_id=event.event_id,
            itinerary_id=event.itinerary_id,
            recipient=event.traveler_email,
            message=build_message(event),
            correlation_id=event.correlation_id,
            processed_at=self._clock(),
        )

        if not self._history.add_if_absent(record):
            logger.info(
                "Evento duplicado: event_id=%s ya estaba en el historial; no se vuelve a notificar "
                "(correlation_id=%s)",
                event.event_id,
                event.correlation_id,
            )
            return NotificationResult(ProcessingStatus.ALREADY_PROCESSED, event.event_id)

        if record.should_be_sent:
            self._sender.send(record.recipient or "", record.message)
        else:
            logger.info(
                "Notificación omitida: event_id=%s itinerary_id=%s. %s",
                event.event_id,
                event.itinerary_id,
                record.status_reason,
            )

        self._unit_of_work.commit()
        logger.info(
            "Notificación registrada: event_id=%s notification_id=%s status=%s correlation_id=%s",
            event.event_id,
            record.id,
            record.status,
            event.correlation_id,
        )
        return NotificationResult(
            ProcessingStatus.PROCESSED, event.event_id, record.id, record.status
        )
