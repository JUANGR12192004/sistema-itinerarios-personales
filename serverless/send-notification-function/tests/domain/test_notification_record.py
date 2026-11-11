"""Pruebas de la entidad NotificationRecord y de la regla del destinatario (ADR-030)."""

from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.domain.exceptions import InvalidNotificationError
from app.domain.notification_record import (
    CHANNEL_SIMULATED_EMAIL,
    NO_RECIPIENT_REASON,
    NotificationRecord,
    NotificationStatus,
)

NOW = datetime(2026, 11, 10, 15, 30, tzinfo=timezone.utc)


def create(recipient: str | None) -> NotificationRecord:
    return NotificationRecord.create(
        event_id=uuid4(),
        itinerary_id=uuid4(),
        recipient=recipient,
        message="Hola Ana: tu itinerario quedó registrado.",
        correlation_id="corr-1",
        processed_at=NOW,
    )


def test_con_correo_queda_enviada_al_correo():
    record = create("ana@example.com")

    assert record.status is NotificationStatus.SENT
    assert record.recipient == "ana@example.com"
    assert record.status_reason is None
    assert record.channel == CHANNEL_SIMULATED_EMAIL
    assert record.should_be_sent is True


def test_quita_los_espacios_del_correo():
    assert create("  ana@example.com ").recipient == "ana@example.com"


@pytest.mark.parametrize("recipient", [None, "", "   "])
def test_sin_correo_queda_omitida_y_explica_el_motivo(recipient):
    record = create(recipient)

    assert record.status is NotificationStatus.SKIPPED
    assert record.recipient is None
    assert record.status_reason == NO_RECIPIENT_REASON
    assert record.should_be_sent is False


def test_cada_registro_tiene_un_id_distinto():
    assert create("ana@example.com").id != create("ana@example.com").id


def test_una_notificacion_enviada_necesita_destinatario():
    record = create("ana@example.com")
    with pytest.raises(InvalidNotificationError):
        replace(record, recipient=None)


def test_una_notificacion_omitida_no_tiene_destinatario():
    record = create(None)
    with pytest.raises(InvalidNotificationError):
        replace(record, recipient="ana@example.com")


def test_una_notificacion_omitida_debe_explicar_el_motivo():
    record = create(None)
    with pytest.raises(InvalidNotificationError):
        replace(record, status_reason=None)


def test_el_mensaje_no_puede_estar_vacio():
    with pytest.raises(InvalidNotificationError):
        replace(create("ana@example.com"), message="   ")


def test_la_fecha_de_procesamiento_debe_tener_zona_horaria():
    with pytest.raises(InvalidNotificationError):
        replace(create("ana@example.com"), processed_at=datetime(2026, 11, 10, 15, 30))
