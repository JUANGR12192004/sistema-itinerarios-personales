"""Implementación del repositorio de itinerarios con SQLAlchemy 2 (modo síncrono).

El repositorio recibe la sesión por constructor (inyección de dependencias).
El commit y el rollback los controla el llamador (el dependency de FastAPI en 3D),
siguiendo el patrón Unit of Work: la sesión agrupa toda la operación.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.ports import ItineraryRepository
from app.domain.itinerary import Itinerary
from app.infrastructure.persistence.models import ItineraryORM


class SqlAlchemyItineraryRepository(ItineraryRepository):
    """Persiste itinerarios en PostgreSQL mediante SQLAlchemy 2."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, itinerary: Itinerary) -> None:
        orm = self._session.get(ItineraryORM, itinerary.id)
        if orm is None:
            self._session.add(_to_orm(itinerary))
        else:
            _apply_to_orm(orm, itinerary)

    def get_by_id(self, itinerary_id: UUID) -> Itinerary | None:
        orm = self._session.get(ItineraryORM, itinerary_id)
        return _to_domain(orm) if orm is not None else None

    def list_all(self) -> list[Itinerary]:
        stmt = select(ItineraryORM).order_by(ItineraryORM.created_at)
        return [_to_domain(orm) for orm in self._session.scalars(stmt).all()]

    def delete(self, itinerary_id: UUID) -> None:
        orm = self._session.get(ItineraryORM, itinerary_id)
        if orm is not None:
            self._session.delete(orm)


# ——— funciones de conversión (privadas al módulo) ———

def _to_orm(itinerary: Itinerary) -> ItineraryORM:
    return ItineraryORM(
        id=itinerary.id,
        traveler_name=itinerary.traveler_name,
        traveler_email=itinerary.traveler_email,
        departure_airport_id=itinerary.departure_airport_id,
        arrival_airport_id=itinerary.arrival_airport_id,
        travel_date=itinerary.travel_date,
        duration_minutes=itinerary.duration_minutes,
        created_at=itinerary.created_at,
        updated_at=itinerary.updated_at,
    )


def _apply_to_orm(orm: ItineraryORM, itinerary: Itinerary) -> None:
    """Actualiza in-place el ORM trackeado por la sesión (unit of work de SQLAlchemy)."""
    orm.traveler_name = itinerary.traveler_name
    orm.traveler_email = itinerary.traveler_email
    orm.departure_airport_id = itinerary.departure_airport_id
    orm.arrival_airport_id = itinerary.arrival_airport_id
    orm.travel_date = itinerary.travel_date
    orm.duration_minutes = itinerary.duration_minutes
    orm.updated_at = itinerary.updated_at


def _to_domain(orm: ItineraryORM) -> Itinerary:
    return Itinerary(
        id=orm.id,
        traveler_name=orm.traveler_name,
        traveler_email=orm.traveler_email,
        departure_airport_id=orm.departure_airport_id,
        arrival_airport_id=orm.arrival_airport_id,
        travel_date=orm.travel_date,
        duration_minutes=orm.duration_minutes,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )
