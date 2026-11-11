"""Excepciones de la capa de aplicación de SendNotificationFunction (ADR-028)."""

from uuid import UUID


class InvalidEventError(Exception):
    """El evento no cumple el contrato v1 de ItineraryCreatedEvent (fallo PERMANENTE).

    Reintentarlo no lo arreglará: el handler responde REJECTED y el Event Trigger
    lo envía a la cola de mensajes fallidos (DLQ).
    """

    def __init__(self, reason: str, event_id: UUID | None = None) -> None:
        self.reason = reason
        self.event_id = event_id
        super().__init__(reason)


class TransientError(Exception):
    """Fallo de INFRAESTRUCTURA: la base de datos del historial no está disponible.

    Es temporal: el mismo evento funcionará cuando vuelva PostgreSQL. Los adaptadores
    de persistencia envuelven sus errores de conexión en esta excepción.

    El nombre de la clase es parte del contrato con el Event Trigger: el Runtime Interface
    Emulator lo informa como `"errorType": "TransientError"` y el trigger reintenta sin
    límite y sin enviar el mensaje a la DLQ. No cambiar el nombre sin cambiar el trigger.
    """
