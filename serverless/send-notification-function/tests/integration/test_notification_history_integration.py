"""Pruebas de integración con el PostgreSQL real de notificaciones (SKIPPED si no está disponible)."""

from uuid import UUID

import pytest
from sqlalchemy import select

from app.application.use_cases import NotifyItineraryCreatedUseCase
from app.domain.notification_record import NO_RECIPIENT_REASON, NotificationRecord
from app.handler import handler, process_event, run_use_case
from app.infrastructure.persistence.models import NotificationHistoryORM
from app.infrastructure.persistence.repository import SqlAlchemyNotificationHistoryRepository
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from tests.fakes import FailingNotificationSender
from tests.integration.conftest import count_rows
from tests.samples import event_payload, make_event


def _record(event_id: UUID | None = None) -> NotificationRecord:
    event = make_event(event_id=event_id)
    return NotificationRecord.create(
        event_id=event.event_id,
        itinerary_id=event.itinerary_id,
        recipient=event.traveler_email,
        message="Hola Ana: tu itinerario quedó registrado.",
        correlation_id=event.correlation_id,
        processed_at=event.occurred_at,
    )


def test_add_if_absent_guarda_todos_los_campos(session_factory):
    record = _record()

    with session_factory() as session:
        assert SqlAlchemyNotificationHistoryRepository(session).add_if_absent(record) is True
        SqlAlchemyUnitOfWork(session).commit()

    with session_factory() as session:
        row = session.execute(select(NotificationHistoryORM)).scalar_one()

    assert row.id == record.id
    assert row.event_id == record.event_id
    assert row.itinerary_id == record.itinerary_id
    assert row.recipient == "ana@example.com"
    assert row.channel == "simulated-email"
    assert row.message == record.message
    assert row.status == "SENT"
    assert row.status_reason is None
    assert row.correlation_id == record.correlation_id
    assert row.processed_at == record.processed_at


def test_add_if_absent_no_inserta_un_event_id_repetido(session_factory):
    first = _record()
    copy = _record(event_id=first.event_id)  # otro id de notificación, mismo evento

    with session_factory() as session:
        repository = SqlAlchemyNotificationHistoryRepository(session)
        assert repository.add_if_absent(first) is True
        SqlAlchemyUnitOfWork(session).commit()

    with session_factory() as session:
        assert SqlAlchemyNotificationHistoryRepository(session).add_if_absent(copy) is False
        SqlAlchemyUnitOfWork(session).commit()

    assert count_rows(session_factory) == 1


def test_procesar_dos_veces_el_mismo_evento_deja_un_solo_registro(session_factory):
    payload = event_payload()

    def run(event):
        return run_use_case(event, session_factory=session_factory)

    first = process_event(payload, run)
    second = process_event(payload, run)

    assert first["status"] == "PROCESSED"
    assert first["notification_status"] == "SENT"
    assert second == {"status": "ALREADY_PROCESSED", "event_id": payload["event_id"]}
    assert count_rows(session_factory) == 1


def test_sin_correo_queda_registrado_como_skipped_con_el_motivo(session_factory):
    payload = event_payload(traveler_email=None)

    response = process_event(payload, lambda event: run_use_case(event, session_factory=session_factory))

    assert response["notification_status"] == "SKIPPED"
    with session_factory() as session:
        row = session.execute(select(NotificationHistoryORM)).scalar_one()
    assert row.recipient is None
    assert row.status == "SKIPPED"
    assert row.status_reason == NO_RECIPIENT_REASON


def test_si_el_envio_falla_no_queda_registro(session_factory):
    with session_factory() as session:
        use_case = NotifyItineraryCreatedUseCase(
            SqlAlchemyNotificationHistoryRepository(session),
            FailingNotificationSender(),
            SqlAlchemyUnitOfWork(session),
        )
        with pytest.raises(RuntimeError):
            use_case.execute(make_event())

    # La sesión se cerró sin commit: el INSERT se deshizo y el evento se puede reintentar
    assert count_rows(session_factory) == 0


def test_handler_de_lambda_de_punta_a_punta(session_factory):
    """Llama a handler(event, context) como lo haría la plataforma, con su engine real."""
    payload = event_payload()

    response = handler(payload, None)

    assert response["status"] == "PROCESSED"
    assert response["event_id"] == payload["event_id"]
    assert count_rows(session_factory) == 1
