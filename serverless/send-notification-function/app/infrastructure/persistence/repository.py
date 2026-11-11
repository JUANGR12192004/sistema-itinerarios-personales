"""Implementación del puerto NotificationHistoryRepository con SQLAlchemy y PostgreSQL."""

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.application.ports import NotificationHistoryRepository
from app.domain.notification_record import NotificationRecord
from app.infrastructure.persistence.errors import translate_database_errors
from app.infrastructure.persistence.models import NotificationHistoryORM


class SqlAlchemyNotificationHistoryRepository(NotificationHistoryRepository):
    """Guarda los NotificationRecord en notification_history.

    Usa la sesión compartida con SqlAlchemyUnitOfWork: el registro queda dentro de la
    transacción y se confirma con `commit()` del caso de uso.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def add_if_absent(self, record: NotificationRecord) -> bool:
        """INSERT ... ON CONFLICT (event_id) DO NOTHING RETURNING id (ADR-030).

        Si ya existe una fila con ese event_id, PostgreSQL no inserta nada y RETURNING no
        devuelve ninguna fila; si la insertó, devuelve su id.
        Si otra transacción está insertando el mismo event_id sin confirmar todavía,
        PostgreSQL espera a que termine: así dos copias simultáneas no se registran ambas.

        Aquí se abre la conexión (es la primera consulta de la invocación): si PostgreSQL
        está apagado, el error aparece en este punto y sale como TransientError.
        """
        statement = (
            insert(NotificationHistoryORM)
            .values(
                id=record.id,
                event_id=record.event_id,
                itinerary_id=record.itinerary_id,
                recipient=record.recipient,
                channel=record.channel,
                message=record.message,
                status=record.status.value,
                status_reason=record.status_reason,
                correlation_id=record.correlation_id,
                processed_at=record.processed_at,
            )
            .on_conflict_do_nothing(index_elements=["event_id"])
            .returning(NotificationHistoryORM.id)
        )
        with translate_database_errors():
            inserted_id = self._session.execute(statement).scalar_one_or_none()
        return inserted_id is not None
