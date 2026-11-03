"""Modelo ORM de SQLAlchemy 2 para la tabla itineraries.

El modelo ORM vive en la capa de infraestructura y no forma parte del dominio.
La entidad de dominio Itinerary y el modelo ItineraryORM son dos objetos distintos;
el repositorio se encarga de convertir entre ellos.
"""

import uuid
from datetime import datetime

import sqlalchemy as sa
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
