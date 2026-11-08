"""Pruebas de integración del Transactional Outbox contra PostgreSQL real (ADR-024, ADR-026).

Comprueban lo que una prueba con fakes no puede demostrar:
- el itinerario y su evento se confirman en la MISMA transacción;
- si el commit no ocurre, no queda ninguno de los dos;
- el payload JSONB conserva el contrato del evento.

Se omiten automáticamente (SKIPPED) cuando PostgreSQL no está disponible.
Requieren las migraciones aplicadas (`alembic upgrade head`).
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.events import ItineraryCreatedEvent
from app.application.ports import UnitOfWork
from app.application.use_cases import CreateItineraryCommand, CreateItineraryUseCase
from app.infrastructure.persistence.models import OutboxEventORM
from app.infrastructure.persistence.outbox_event_publisher import OutboxEventPublisher
from app.infrastructure.persistence.repository import SqlAlchemyItineraryRepository
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from tests.fakes import FakeAirportCatalog

BOGOTA = timezone(timedelta(hours=-5))


class FailingUnitOfWork(UnitOfWork):
    """Simula que el commit falla (por ejemplo, se cae PostgreSQL en ese momento)."""

    def commit(self) -> None:
        raise RuntimeError("commit simulado fallido")


def _command() -> CreateItineraryCommand:
    return CreateItineraryCommand(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=(datetime.now(BOGOTA) + timedelta(days=30)).replace(microsecond=0),
        duration_minutes=75,
        traveler_email="ana@example.com",
        correlation_id="cid-outbox",
    )


def _use_case(session: Session, unit_of_work: UnitOfWork | None = None) -> CreateItineraryUseCase:
    return CreateItineraryUseCase(
        repo=SqlAlchemyItineraryRepository(session),
        airport_catalog=FakeAirportCatalog(),
        unit_of_work=unit_of_work or SqlAlchemyUnitOfWork(session),
        event_publisher=OutboxEventPublisher(session),
    )


def _outbox_rows(session: Session) -> list[OutboxEventORM]:
    return list(session.scalars(select(OutboxEventORM)).all())


def test_itinerario_y_evento_se_confirman_juntos(db_session):
    itinerary = _use_case(db_session).execute(_command())

    # Otra sesión solo ve lo que ya está confirmado (commit)
    with Session(db_session.get_bind()) as other:
        assert SqlAlchemyItineraryRepository(other).get_by_id(itinerary.id) is not None
        rows = _outbox_rows(other)

    assert len(rows) == 1
    row = rows[0]
    assert row.aggregate_type == "itinerary"
    assert row.aggregate_id == itinerary.id
    assert row.event_type == "itinerary.created"
    assert row.event_version == 1
    assert row.published_at is None
    assert row.attempts == 0
    assert row.last_error is None
    assert str(row.id) == row.payload["event_id"]


def test_sin_commit_no_queda_ni_itinerario_ni_evento(db_session):
    """Si el commit falla, el rollback deshace las dos escrituras: no hay double write."""
    with pytest.raises(RuntimeError):
        _use_case(db_session, FailingUnitOfWork()).execute(_command())
    db_session.rollback()  # lo que hace get_db_session ante una excepción

    with Session(db_session.get_bind()) as other:
        assert SqlAlchemyItineraryRepository(other).list_all() == []
        assert _outbox_rows(other) == []


def test_el_payload_jsonb_conserva_el_contrato(db_session):
    _use_case(db_session).execute(_command())

    with Session(db_session.get_bind()) as other:
        payload = _outbox_rows(other)[0].payload

    rebuilt = ItineraryCreatedEvent.from_dict(payload)
    assert rebuilt.to_dict() == payload
    assert payload["correlation_id"] == "cid-outbox"
    assert payload["data"]["travel_date"].endswith("-05:00")
