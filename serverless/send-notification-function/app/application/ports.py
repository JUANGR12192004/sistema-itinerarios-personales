"""Puertos (interfaces) de la capa de aplicación de SendNotificationFunction.

El caso de uso solo depende de estos contratos. Las implementaciones reales están en
`infrastructure` (PostgreSQL y correo simulado) y las de prueba en `tests/fakes.py`.
"""

from abc import ABC, abstractmethod

from app.domain.notification_record import NotificationRecord


class NotificationHistoryRepository(ABC):
    """Historial de notificaciones (tabla notification_history, ADR-029).

    Raises:
        TransientError: la base de datos del historial no está disponible.
    """

    @abstractmethod
    def add_if_absent(self, record: NotificationRecord) -> bool:
        """Registra la notificación si no existe otra con el mismo `event_id`.

        Devuelve True si la registró y False si el evento ya estaba en el historial
        (idempotencia, ADR-030). El registro queda pendiente hasta el commit.
        """


class NotificationSender(ABC):
    """Envía la notificación al viajero. En este proyecto el envío es simulado."""

    @abstractmethod
    def send(self, recipient: str, message: str) -> None:
        """Envía el mensaje al destinatario."""


class UnitOfWork(ABC):
    """Confirma (commit) los cambios de la transacción actual.

    Raises:
        TransientError: la base de datos del historial no está disponible.
    """

    @abstractmethod
    def commit(self) -> None:
        """Confirma en la base de datos los cambios pendientes."""
