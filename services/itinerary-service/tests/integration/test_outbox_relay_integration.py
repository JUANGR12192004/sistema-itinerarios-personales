"""Prueba de integración del recorrido completo: API (caso de uso) → outbox → relay → RabbitMQ.

Necesita PostgreSQL (con `alembic upgrade head`) y RabbitMQ; si falta alguno, SKIPPED.

ATENCIÓN: el fixture rabbitmq_channel vacía la cola notification.itinerary-created
antes y después de cada prueba.
"""

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from app.application.outbox_relay import OutboxRelay, RelayResult
from app.application.ports import UnitOfWork
from app.application.use_cases import CreateItineraryCommand, CreateItineraryUseCase
from app.config import get_settings
from app.infrastructure.messaging.rabbitmq_event_publisher import RabbitMQEventPublisher
from app.infrastructure.messaging.topology import QUEUE_NOTIFICATIONS
from app.infrastructure.persistence.models import OutboxEventORM
from app.infrastructure.persistence.outbox_event_publisher import OutboxEventPublisher
from app.infrastructure.persistence.outbox_repository import SqlAlchemyOutboxRepository
from app.infrastructure.persistence.repository import SqlAlchemyItineraryRepository
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from tests.fakes import FakeAirportCatalog
from tests.integration.conftest import RABBITMQ_TIMEOUT_SECONDS


class FailingUnitOfWork(UnitOfWork):
    """Simula que el relay se cae justo antes del commit que marca los publicados."""

    def commit(self) -> None:
        raise RuntimeError("el relay se detuvo antes del commit (simulado)")


def _create_itinerary(session: Session):
    """Crea un itinerario como lo hace POST /itineraries: itinerario + evento en la outbox."""
    use_case = CreateItineraryUseCase(
        repo=SqlAlchemyItineraryRepository(session),
        airport_catalog=FakeAirportCatalog(),
        unit_of_work=SqlAlchemyUnitOfWork(session),
        event_publisher=OutboxEventPublisher(session),
    )
    return use_case.execute(
        CreateItineraryCommand(
            traveler_name="Ana Pérez",
            departure_airport_id=1,
            arrival_airport_id=5,
            travel_date=datetime.now(timezone.utc) + timedelta(days=30),
            duration_minutes=75,
            correlation_id="cid-relay-e2e",
        )
    )


def _relay(session: Session, unit_of_work: UnitOfWork | None = None) -> OutboxRelay:
    return OutboxRelay(
        outbox=SqlAlchemyOutboxRepository(session),
        publisher=RabbitMQEventPublisher(get_settings().rabbitmq_url, RABBITMQ_TIMEOUT_SECONDS),
        unit_of_work=unit_of_work or SqlAlchemyUnitOfWork(session),
        batch_size=10,
    )


def test_el_relay_publica_el_evento_pendiente_en_la_cola(db_session, rabbitmq_channel):
    itinerary = _create_itinerary(db_session)

    result = _relay(db_session).run_once()

    assert result == RelayResult(published=1, failed=0)
    method, properties, body = rabbitmq_channel.basic_get(QUEUE_NOTIFICATIONS, auto_ack=True)
    assert method is not None, "La cola no recibió el mensaje"
    payload = json.loads(body)
    assert payload["data"]["itinerary_id"] == str(itinerary.id)
    assert payload["correlation_id"] == "cid-relay-e2e"
    assert properties.message_id == payload["event_id"]

    with Session(db_session.get_bind()) as other:
        row = other.get(OutboxEventORM, UUID(properties.message_id))
    assert row.published_at is not None


def test_si_el_relay_cae_antes_del_commit_el_evento_se_publica_dos_veces(db_session, rabbitmq_channel):
    """Entrega "al menos una vez": puede haber duplicados con el MISMO event_id (message_id)."""
    _create_itinerary(db_session)

    with pytest.raises(RuntimeError):
        _relay(db_session, FailingUnitOfWork()).run_once()
    db_session.rollback()  # lo que hace run_cycle: la marca de publicado se pierde

    _relay(db_session).run_once()

    first = rabbitmq_channel.basic_get(QUEUE_NOTIFICATIONS, auto_ack=True)
    second = rabbitmq_channel.basic_get(QUEUE_NOTIFICATIONS, auto_ack=True)
    assert first[0] is not None and second[0] is not None, "Se esperaban dos copias del evento"
    assert first[1].message_id == second[1].message_id
