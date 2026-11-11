"""Eventos de ejemplo para las pruebas (contrato ItineraryCreatedEvent v1, ADR-020)."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.application.events import ItineraryCreatedEvent

EVENTS_DIR = Path(__file__).resolve().parent.parent / "events"

_BASE_PAYLOAD: dict[str, Any] = {
    "event_id": "7d9f1c2e-4b5a-4e8f-9a1b-2c3d4e5f6a7b",
    "event_type": "itinerary.created",
    "event_version": 1,
    "occurred_at": "2026-11-10T15:30:00Z",
    "producer": "itinerary-service",
    "correlation_id": "3f2a8c1d-0b9e-4d7f-a6c5-1e2d3c4b5a69",
    "data": {
        "itinerary_id": "0c1d2e3f-4a5b-4c6d-8e7f-9a0b1c2d3e4f",
        "traveler_name": "Ana Pérez",
        "traveler_email": "ana@example.com",
        "departure_airport_id": 1,
        "arrival_airport_id": 5,
        "travel_date": "2026-12-15T08:00:00-05:00",
        "duration_minutes": 75,
    },
}


def event_payload(event_id: str | None = None, **data_overrides: Any) -> dict[str, Any]:
    """Evento válido como JSON (dict). `data_overrides` cambia campos de `data`."""
    payload = deepcopy(_BASE_PAYLOAD)
    payload["event_id"] = event_id or str(uuid4())
    payload["data"].update(data_overrides)
    return payload


def make_event(traveler_email: str | None = "ana@example.com", event_id: UUID | None = None) -> ItineraryCreatedEvent:
    """Evento ya validado, como lo recibe el caso de uso."""
    return ItineraryCreatedEvent(
        event_id=event_id or uuid4(),
        occurred_at=datetime(2026, 11, 10, 15, 30, tzinfo=timezone.utc),
        correlation_id="3f2a8c1d-0b9e-4d7f-a6c5-1e2d3c4b5a69",
        itinerary_id=UUID("0c1d2e3f-4a5b-4c6d-8e7f-9a0b1c2d3e4f"),
        traveler_name="Ana Pérez",
        traveler_email=traveler_email,
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=datetime(2026, 12, 15, 8, 0, tzinfo=timezone(timedelta(hours=-5))),
        duration_minutes=75,
    )
