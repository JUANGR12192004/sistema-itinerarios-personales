"""Entidad NotificationRecord: el registro de un aviso procesado (ADR-030).

Cada evento ItineraryCreatedEvent procesado deja un NotificationRecord en el historial.
El `event_id` es la clave de idempotencia: no puede haber dos registros con el mismo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.exceptions import InvalidNotificationError

CHANNEL_SIMULATED_EMAIL = "simulated-email"

NO_RECIPIENT_REASON = (
    "El itinerario no tiene traveler_email: no hay destinatario para la notificación"
)


class NotificationStatus(StrEnum):
    """Resultado de la notificación.

    SENT:    se envió (simulado) al correo del viajero.
    SKIPPED: no se envió porque el itinerario no tiene correo (el correo es opcional, ADR-018).
    """

    SENT = "SENT"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class NotificationRecord:
    """Registro de un aviso. Se construye con create(), que aplica la regla del destinatario."""

    id: UUID
    event_id: UUID
    itinerary_id: UUID
    recipient: str | None
    channel: str
    message: str
    status: NotificationStatus
    status_reason: str | None
    correlation_id: str | None
    processed_at: datetime

    def __post_init__(self) -> None:
        """Invariantes: se cumplen aunque el registro se construya sin create()."""
        if not self.message.strip():
            raise InvalidNotificationError("El mensaje de la notificación no puede estar vacío.")
        if self.processed_at.tzinfo is None:
            raise InvalidNotificationError("La fecha de procesamiento debe incluir zona horaria.")
        if self.status is NotificationStatus.SENT and not self.recipient:
            raise InvalidNotificationError("Una notificación enviada necesita un destinatario.")
        if self.status is NotificationStatus.SKIPPED and (self.recipient or not self.status_reason):
            raise InvalidNotificationError(
                "Una notificación omitida no tiene destinatario y debe explicar el motivo."
            )

    @classmethod
    def create(
        cls,
        event_id: UUID,
        itinerary_id: UUID,
        recipient: str | None,
        message: str,
        correlation_id: str | None,
        processed_at: datetime,
    ) -> NotificationRecord:
        """Crea el registro aplicando la regla del destinatario.

        - Con correo: status SENT y el correo como destinatario.
        - Sin correo (None o vacío): status SKIPPED, sin destinatario y con el motivo.
        """
        email = recipient.strip() if recipient else ""
        if email:
            status, final_recipient, reason = NotificationStatus.SENT, email, None
        else:
            status, final_recipient, reason = NotificationStatus.SKIPPED, None, NO_RECIPIENT_REASON

        return cls(
            id=uuid4(),
            event_id=event_id,
            itinerary_id=itinerary_id,
            recipient=final_recipient,
            channel=CHANNEL_SIMULATED_EMAIL,
            message=message,
            status=status,
            status_reason=reason,
            correlation_id=correlation_id,
            processed_at=processed_at,
        )

    @property
    def should_be_sent(self) -> bool:
        """Indica si hay que enviar la notificación (solo cuando hay destinatario)."""
        return self.status is NotificationStatus.SENT
