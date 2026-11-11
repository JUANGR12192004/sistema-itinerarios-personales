"""Modelo ORM de SQLAlchemy 2 para la tabla notification_history (ADR-029).

El modelo ORM vive en infraestructura. La entidad de dominio NotificationRecord y
NotificationHistoryORM son objetos distintos; el repositorio convierte entre ellos.
"""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa de los modelos de la función."""


class NotificationHistoryORM(Base):
    """Fila de notification_history: un aviso procesado."""

    __tablename__ = "notification_history"
    __table_args__ = (
        # Clave de idempotencia: un solo registro por evento (ADR-030)
        sa.UniqueConstraint("event_id", name="uq_notification_history_event_id"),
        sa.CheckConstraint("status IN ('SENT', 'SKIPPED')", name="ck_notification_history_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    event_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    # Referencia por id al itinerario: está en otra base de datos, no hay clave foránea
    itinerary_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    recipient: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    channel: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    message: Mapped[str] = mapped_column(sa.Text, nullable=False)
    status: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    status_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    processed_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
