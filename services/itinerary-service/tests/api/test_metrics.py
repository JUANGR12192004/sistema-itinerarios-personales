"""Pruebas del endpoint /metrics de Itinerary Service (Fase 9C, ADR-038)."""

import re
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_airport_catalog,
    get_event_publisher,
    get_itinerary_repository,
    get_unit_of_work,
)
from app.main import app
from app.metrics import ITINERARIES_CREATED
from tests.fakes import FakeAirportCatalog, FakeEventPublisher, FakeItineraryRepository, FakeUnitOfWork

FUTURE = datetime.now(timezone.utc) + timedelta(days=30)

BODY_VALIDO = {
    "traveler_name": "Ana Pérez",
    "departure_airport_id": 1,
    "arrival_airport_id": 5,
    "travel_date": FUTURE.isoformat(),
    "duration_minutes": 75,
}


@pytest.fixture(autouse=True)
def limpiar_overrides():
    yield
    app.dependency_overrides.clear()


def _make_client() -> TestClient:
    app.dependency_overrides[get_itinerary_repository] = lambda: FakeItineraryRepository()
    app.dependency_overrides[get_airport_catalog] = lambda: FakeAirportCatalog()
    app.dependency_overrides[get_unit_of_work] = lambda: FakeUnitOfWork()
    app.dependency_overrides[get_event_publisher] = lambda: FakeEventPublisher()
    return TestClient(app)


def test_metrics_devuelve_200() -> None:
    response = TestClient(app).get("/metrics")

    assert response.status_code == 200


def test_metrics_content_type_es_texto() -> None:
    response = TestClient(app).get("/metrics")

    assert response.headers["content-type"].startswith("text/plain")


def test_metrics_contiene_contadores_http() -> None:
    client = _make_client()
    client.get("/health")
    response = client.get("/metrics")

    body = response.text
    assert "http_requests_total" in body
    assert "http_request_duration_seconds" in body


def test_metrics_contiene_contador_de_negocio() -> None:
    response = TestClient(app).get("/metrics")

    assert "itineraries_created_total" in response.text


def test_crear_itinerario_incrementa_el_contador() -> None:
    """Crear un itinerario exitosamente incrementa itineraries_created_total."""
    client = _make_client()

    # Lee el valor actual del contador antes de crear
    antes = ITINERARIES_CREATED._value.get()  # type: ignore[attr-defined]

    client.post("/itineraries", json=BODY_VALIDO)

    despues = ITINERARIES_CREATED._value.get()  # type: ignore[attr-defined]
    assert despues == antes + 1


def test_metrics_usa_plantilla_de_ruta_no_id_concreto() -> None:
    """El label `path` debe ser la plantilla (/itineraries/{itinerary_id}), no un UUID concreto."""
    client = _make_client()
    # Crea uno para que exista un ID al que hacer GET
    res = client.post("/itineraries", json=BODY_VALIDO)
    itinerary_id = res.json()["id"]
    client.get(f"/itineraries/{itinerary_id}")
    response = client.get("/metrics")

    body = response.text
    assert 'path="/itineraries/{itinerary_id}"' in body
    assert re.search(r'path="/itineraries/[0-9a-f-]{36}"', body) is None
