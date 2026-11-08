"""Pruebas de integración de SqlAlchemyOutboxRepository y del relay contra PostgreSQL real.

Comprueban lo que los fakes no pueden simular: el orden y el filtro de pendientes en SQL,
el bloqueo con FOR UPDATE SKIP LOCKED entre dos sesiones (dos relays) y que un fallo de
RabbitMQ deja el evento pendiente con su intento registrado (ADR-025).

Se omiten (SKIPPED) cuando PostgreSQL no está disponible. Requieren `alembic upgrade head`.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.application.events import ItineraryCreatedEvent
from app.application.outbox_relay import OutboxRelay, RelayResult
from app.domain.itinerary import Itinerary
from app.infrastructure.messaging.rabbitmq_event_publisher import RabbitMQEventPublisher
from app.infrastructure.persistence.models import OutboxEventORM
from app.infrastructure.persistence.outbox_event_publisher import OutboxEventPublisher
from app.infrastructure.persistence.outbox_repository import SqlAlchemyOutboxRepository
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork

BASE_TIME = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)
# Puerto donde no escucha nadie: simula RabbitMQ caído sin tener que detenerlo
UNREACHABLE_RABBITMQ_URL = "amqp://guest:guest@127.0.0.1:1/%2F"


def _store_events(session: Session, count: int) -> list[ItineraryCreatedEvent]:
    """Registra `count` eventos en la outbox (sin itinerario: basta con la fila) y confirma.

    Cada evento ocurre un minuto después del anterior, para conocer el orden esperado.
    """
    events = []
    for minutes in range(count):
        itinerary = Itinerary.create(
            traveler_name=f"Viajero {minutes}",
            departure_airport_id=1,
            arrival_airport_id=5,
            travel_date=datetime.now(timezone.utc) + timedelta(days=30),
            duration_minutes=75,
        )
        event = ItineraryCreatedEvent.from_itinerary(itinerary, "cid-repo")
        event = ItineraryCreatedEvent.from_dict(
            {**event.to_dict(), "occurred_at": (BASE_TIME + timedelta(minutes=minutes)).isoformat()}
        )
        OutboxEventPublisher(session).publish(event)
        events.append(event)
    session.commit()
    return events


def test_get_pending_devuelve_los_pendientes_en_orden(db_session):
    events = _store_events(db_session, 3)

    pending = SqlAlchemyOutboxRepository(db_session).get_pending(10)

    assert [m.id for m in pending] == [e.event_id for e in events]
    assert pending[0].payload == events[0].to_dict()


def test_get_pending_respeta_el_limite(db_session):
    events = _store_events(db_session, 3)

    pending = SqlAlchemyOutboxRepository(db_session).get_pending(2)

    assert [m.id for m in pending] == [events[0].event_id, events[1].event_id]


def test_mark_published_saca_el_evento_de_los_pendientes(db_session):
    first, second = _store_events(db_session, 2)
    repo = SqlAlchemyOutboxRepository(db_session)

    repo.mark_published(first.event_id, BASE_TIME)
    db_session.commit()

    assert [m.id for m in repo.get_pending(10)] == [second.event_id]
    assert db_session.get(OutboxEventORM, first.event_id).published_at == BASE_TIME


def test_mark_failed_suma_intentos_y_guarda_el_error(db_session):
    (event,) = _store_events(db_session, 1)
    repo = SqlAlchemyOutboxRepository(db_session)

    repo.mark_failed(event.event_id, "primer error")
    repo.mark_failed(event.event_id, "segundo error")
    db_session.commit()

    (pending,) = repo.get_pending(10)
    assert pending.attempts == 2
    assert pending.last_error == "segundo error"
    assert pending.published_at is None


def test_skip_locked_dos_relays_no_toman_el_mismo_evento(db_session):
    """El relay A bloquea dos eventos; el relay B, al mismo tiempo, solo ve el tercero."""
    events = _store_events(db_session, 3)

    locked_by_a = SqlAlchemyOutboxRepository(db_session).get_pending(2)  # transacción abierta

    with Session(db_session.get_bind()) as session_b:
        # Si SKIP LOCKED no funcionara, B esperaría a A; el lock_timeout evita que la prueba se cuelgue
        session_b.execute(text("SET LOCAL lock_timeout = '2s'"))
        seen_by_b = SqlAlchemyOutboxRepository(session_b).get_pending(10)
        session_b.rollback()

    db_session.rollback()  # A libera sus bloqueos
    assert [m.id for m in locked_by_a] == [events[0].event_id, events[1].event_id]
    assert [m.id for m in seen_by_b] == [events[2].event_id]


def test_relay_con_rabbitmq_caido_deja_el_evento_pendiente(db_session):
    """El double write resuelto: RabbitMQ no está, pero el evento no se pierde."""
    (event,) = _store_events(db_session, 1)
    relay = OutboxRelay(
        outbox=SqlAlchemyOutboxRepository(db_session),
        publisher=RabbitMQEventPublisher(UNREACHABLE_RABBITMQ_URL, timeout_seconds=1.0),
        unit_of_work=SqlAlchemyUnitOfWork(db_session),
        batch_size=10,
    )

    result = relay.run_once()

    assert result == RelayResult(published=0, failed=1)
    with Session(db_session.get_bind()) as other:
        row = other.get(OutboxEventORM, event.event_id)
    assert row.published_at is None
    assert row.attempts == 1
    assert "No se pudo conectar con RabbitMQ" in row.last_error
