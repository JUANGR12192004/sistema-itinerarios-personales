"""Implementación del puerto OutboxRepository con SQLAlchemy 2 (ADR-025).

La lectura de pendientes usa `SELECT ... FOR UPDATE SKIP LOCKED`:
- FOR UPDATE bloquea las filas leídas hasta el fin de la transacción (commit o rollback);
- SKIP LOCKED hace que otro relay SALTE esas filas en vez de esperar por ellas.
Así dos relays que corren a la vez nunca toman el mismo evento.

El commit lo hace el relay con UnitOfWork, una vez por lote: hacerlo antes
liberaría los bloqueos de los eventos que todavía no se han publicado.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.application.outbox import OutboxMessage
from app.application.ports import OutboxRepository
from app.infrastructure.persistence.models import OutboxEventORM


class SqlAlchemyOutboxRepository(OutboxRepository):
    """Lee y marca los eventos de `outbox_events` en PostgreSQL."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_pending(self, limit: int) -> list[OutboxMessage]:
        # Misma condición que el índice parcial ix_outbox_events_pending, para que PostgreSQL lo use
        stmt = (
            select(OutboxEventORM)
            .where(OutboxEventORM.published_at.is_(None), OutboxEventORM.failed_at.is_(None))
            .order_by(OutboxEventORM.occurred_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return [_to_message(orm) for orm in self._session.scalars(stmt).all()]

    def mark_published(self, message_id: UUID, published_at: datetime) -> None:
        self._session.execute(
            update(OutboxEventORM)
            .where(OutboxEventORM.id == message_id)
            .values(published_at=published_at),
            execution_options={"synchronize_session": False},
        )

    def mark_failed(self, message_id: UUID, error: str) -> None:
        # attempts + 1 se calcula en la base de datos, no en Python
        self._session.execute(
            update(OutboxEventORM)
            .where(OutboxEventORM.id == message_id)
            .values(attempts=OutboxEventORM.attempts + 1, last_error=error),
            execution_options={"synchronize_session": False},
        )

    def mark_dead(self, message_id: UUID, failed_at: datetime, error: str) -> None:
        self._session.execute(
            update(OutboxEventORM)
            .where(OutboxEventORM.id == message_id)
            .values(attempts=OutboxEventORM.attempts + 1, last_error=error, failed_at=failed_at),
            execution_options={"synchronize_session": False},
        )


def _to_message(orm: OutboxEventORM) -> OutboxMessage:
    return OutboxMessage(
        id=orm.id,
        aggregate_type=orm.aggregate_type,
        aggregate_id=orm.aggregate_id,
        event_type=orm.event_type,
        event_version=orm.event_version,
        payload=orm.payload,
        occurred_at=orm.occurred_at,
        published_at=orm.published_at,
        attempts=orm.attempts,
        last_error=orm.last_error,
        failed_at=orm.failed_at,
        traceparent=orm.traceparent,
    )
