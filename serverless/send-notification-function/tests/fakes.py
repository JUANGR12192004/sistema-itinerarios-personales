"""Implementaciones falsas de los puertos, para probar el caso de uso sin PostgreSQL."""

from uuid import UUID

from app.application.exceptions import TransientError
from app.application.ports import NotificationHistoryRepository, NotificationSender, UnitOfWork
from app.domain.notification_record import NotificationRecord


class FakeNotificationHistoryRepository(NotificationHistoryRepository):
    """Historial en memoria, indexado por event_id (como la restricción única de la tabla)."""

    def __init__(self) -> None:
        self.records: dict[UUID, NotificationRecord] = {}

    def add_if_absent(self, record: NotificationRecord) -> bool:
        if record.event_id in self.records:
            return False
        self.records[record.event_id] = record
        return True


class UnavailableNotificationHistoryRepository(NotificationHistoryRepository):
    """Simula PostgreSQL apagado."""

    def add_if_absent(self, record: NotificationRecord) -> bool:
        raise TransientError("La base de datos del historial de notificaciones no está disponible")


class FakeNotificationSender(NotificationSender):
    """Guarda los envíos en una lista para comprobarlos."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, recipient: str, message: str) -> None:
        self.sent.append((recipient, message))


class FailingNotificationSender(NotificationSender):
    """Simula un fallo al enviar."""

    def send(self, recipient: str, message: str) -> None:
        raise RuntimeError("El proveedor de correo falló")


class FakeUnitOfWork(UnitOfWork):
    """Cuenta los commits."""

    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1
