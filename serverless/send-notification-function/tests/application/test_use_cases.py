"""Pruebas de NotifyItineraryCreatedUseCase con puertos falsos (ADR-030)."""

from datetime import datetime, timezone

import pytest

from app.application.exceptions import TransientError
from app.application.use_cases import (
    NotifyItineraryCreatedUseCase,
    ProcessingStatus,
    build_message,
)
from app.domain.notification_record import CHANNEL_SIMULATED_EMAIL, NotificationStatus
from tests.fakes import (
    FailingNotificationSender,
    FakeNotificationHistoryRepository,
    FakeNotificationSender,
    FakeUnitOfWork,
    UnavailableNotificationHistoryRepository,
)
from tests.samples import make_event

NOW = datetime(2026, 11, 10, 16, 0, tzinfo=timezone.utc)


@pytest.fixture
def history():
    return FakeNotificationHistoryRepository()


@pytest.fixture
def sender():
    return FakeNotificationSender()


@pytest.fixture
def unit_of_work():
    return FakeUnitOfWork()


@pytest.fixture
def use_case(history, sender, unit_of_work):
    return NotifyItineraryCreatedUseCase(history, sender, unit_of_work, clock=lambda: NOW)


def test_con_correo_envia_registra_y_confirma(use_case, history, sender, unit_of_work):
    event = make_event(traveler_email="ana@example.com")

    result = use_case.execute(event)

    assert result.status is ProcessingStatus.PROCESSED
    assert result.event_id == event.event_id
    assert result.notification_status is NotificationStatus.SENT
    assert sender.sent == [("ana@example.com", build_message(event))]
    assert unit_of_work.commits == 1

    record = history.records[event.event_id]
    assert record.id == result.notification_id
    assert record.itinerary_id == event.itinerary_id
    assert record.channel == CHANNEL_SIMULATED_EMAIL
    assert record.correlation_id == event.correlation_id
    assert record.processed_at == NOW


def test_sin_correo_registra_omitida_sin_enviar(use_case, history, sender, unit_of_work):
    event = make_event(traveler_email=None)

    result = use_case.execute(event)

    assert result.status is ProcessingStatus.PROCESSED
    assert result.notification_status is NotificationStatus.SKIPPED
    assert sender.sent == []
    assert unit_of_work.commits == 1
    record = history.records[event.event_id]
    assert record.recipient is None
    assert "traveler_email" in (record.status_reason or "")


def test_un_evento_duplicado_no_se_vuelve_a_enviar_ni_a_registrar(use_case, history, sender, unit_of_work):
    event = make_event()

    first = use_case.execute(event)
    second = use_case.execute(event)

    assert first.status is ProcessingStatus.PROCESSED
    assert second.status is ProcessingStatus.ALREADY_PROCESSED
    assert second.event_id == event.event_id
    assert second.notification_id is None
    assert len(sender.sent) == 1
    assert len(history.records) == 1
    assert unit_of_work.commits == 1


def test_si_el_envio_falla_no_hay_commit(history, unit_of_work):
    use_case = NotifyItineraryCreatedUseCase(history, FailingNotificationSender(), unit_of_work)

    with pytest.raises(RuntimeError):
        use_case.execute(make_event())

    # Sin commit, la transacción real se deshace y el evento se puede reintentar
    assert unit_of_work.commits == 0


def test_si_la_base_de_datos_no_esta_disponible_propaga_transient_error(sender, unit_of_work):
    use_case = NotifyItineraryCreatedUseCase(
        UnavailableNotificationHistoryRepository(), sender, unit_of_work
    )

    with pytest.raises(TransientError):
        use_case.execute(make_event())

    assert sender.sent == []
    assert unit_of_work.commits == 0


def test_el_mensaje_incluye_los_datos_del_itinerario():
    event = make_event()

    message = build_message(event)

    assert "Ana Pérez" in message
    assert str(event.itinerary_id) in message
    assert "aeropuerto 1" in message
    assert "aeropuerto 5" in message
    assert "2026-12-15T08:00:00-05:00" in message
    assert "75 minutos" in message
