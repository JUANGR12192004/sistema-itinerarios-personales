"""Pruebas del handler de Lambda con un caso de uso falso (ADR-028)."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from app.application.exceptions import TransientError
from app.application.use_cases import (
    NotificationResult,
    NotifyItineraryCreatedUseCase,
    ProcessingStatus,
)
from app.domain.notification_record import NotificationStatus
from app.handler import build_use_case, process_event
from tests.samples import event_payload


def test_procesado_responde_processed_con_la_notificacion():
    notification_id = uuid4()

    def run(event):
        return NotificationResult(
            ProcessingStatus.PROCESSED, event.event_id, notification_id, NotificationStatus.SENT
        )

    payload = event_payload()
    response = process_event(payload, run)

    assert response == {
        "status": "PROCESSED",
        "event_id": payload["event_id"],
        "notification_id": str(notification_id),
        "notification_status": "SENT",
    }


def test_duplicado_responde_already_processed():
    payload = event_payload()

    response = process_event(
        payload, lambda event: NotificationResult(ProcessingStatus.ALREADY_PROCESSED, event.event_id)
    )

    assert response == {"status": "ALREADY_PROCESSED", "event_id": payload["event_id"]}


def test_evento_invalido_responde_rejected_sin_ejecutar_el_caso_de_uso():
    calls = []
    payload = event_payload(duration_minutes=0)

    response = process_event(payload, calls.append)

    assert response["status"] == "REJECTED"
    assert response["event_id"] == payload["event_id"]
    assert "data.duration_minutes" in response["reason"]
    assert calls == []


def test_rechazo_sin_event_id_legible():
    response = process_event("no es un objeto", lambda event: None)

    assert response["status"] == "REJECTED"
    assert response["event_id"] is None


def test_transient_error_se_propaga_para_que_el_rie_lo_informe_como_error_type():
    def run(event):
        raise TransientError("La base de datos del historial de notificaciones no está disponible")

    with pytest.raises(TransientError):
        process_event(event_payload(), run)


def test_otros_errores_tambien_se_propagan():
    def run(event):
        raise KeyError("error de programación")

    with pytest.raises(KeyError):
        process_event(event_payload(), run)


def test_build_use_case_ensambla_el_caso_de_uso():
    assert isinstance(build_use_case(Session()), NotifyItineraryCreatedUseCase)


def test_el_event_id_de_la_respuesta_es_el_del_evento():
    event_id = "7d9f1c2e-4b5a-4e8f-9a1b-2c3d4e5f6a7b"

    response = process_event(
        event_payload(event_id=event_id),
        lambda event: NotificationResult(ProcessingStatus.ALREADY_PROCESSED, event.event_id),
    )

    assert UUID(response["event_id"]) == UUID(event_id)
