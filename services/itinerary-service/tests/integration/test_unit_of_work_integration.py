"""Prueba de integración de SqlAlchemyUnitOfWork contra PostgreSQL real.

Verifica que, después de `commit()`, el itinerario es visible desde OTRA sesión:
es decir, que el commit del caso de uso realmente confirma los datos (ADR-026).

Se omite automáticamente (SKIPPED) cuando PostgreSQL no está disponible.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.domain.itinerary import Itinerary
from app.infrastructure.persistence.repository import SqlAlchemyItineraryRepository
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


def test_commit_hace_visible_el_itinerario_en_otra_sesion(db_session):
    itinerary = Itinerary.create(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=datetime.now(timezone.utc) + timedelta(days=30),
        duration_minutes=75,
    )
    SqlAlchemyItineraryRepository(db_session).save(itinerary)

    SqlAlchemyUnitOfWork(db_session).commit()

    with Session(db_session.get_bind()) as other_session:
        found = SqlAlchemyItineraryRepository(other_session).get_by_id(itinerary.id)
    assert found is not None
    assert found.id == itinerary.id
