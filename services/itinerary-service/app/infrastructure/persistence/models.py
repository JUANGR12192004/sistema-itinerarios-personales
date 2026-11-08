"""Modelos ORM de SQLAlchemy 2 para las tablas itineraries y outbox_events.

Los modelos ORM viven en la capa de infraestructura y no forman parte del dominio.
La entidad de dominio Itinerary y el modelo ItineraryORM son dos objetos distintos;
el repositorio se encarga de convertir entre ellos. Lo mismo ocurre con
OutboxMessage (aplicación) y OutboxEventORM.
"""

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa compartida por todos los modelos del servicio."""


class ItineraryORM(Base):
    """Fila de la tabla itineraries tal como la ve SQLAlchemy."""

    __tablename__ = "itineraries"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    traveler_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    traveler_email: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    departure_airport_id: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    arrival_airport_id: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    travel_date: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)


class OutboxEventORM(Base):
    """Fila de la tabla outbox_events: un evento registrado para publicar (ADR-024)."""

    __tablename__ = "outbox_events"
    __table_args__ = (
        # Índice parcial: solo contiene las filas pendientes (published_at IS NULL),
        # que son las que busca el relay ordenadas por occurred_at.
        sa.Index(
            "ix_outbox_events_pending",
            "occurred_at",
            postgresql_where=sa.text("published_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    aggregate_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    event_version: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    last_error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
