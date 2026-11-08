"""Pruebas de la API REST de Itinerary Service con dependencias falsas inyectadas.

Usan TestClient de FastAPI con dependency_overrides para sustituir los puertos
reales (PostgreSQL, Airport Service) por implementaciones falsas en memoria.
No hacen llamadas reales a ningún servicio externo.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_airport_catalog,
    get_event_publisher,
    get_itinerary_repository,
    get_unit_of_work,
)
from app.application.ports import ItineraryRepository
from app.main import app
from tests.fakes import (
    FakeAirportCatalog,
    FakeEventPublisher,
    FakeItineraryRepository,
    FakeUnitOfWork,
)

FUTURE = datetime.now(timezone.utc) + timedelta(days=30)

BODY_VALIDO = {
    "traveler_name": "Ana Pérez",
    "departure_airport_id": 1,
    "arrival_airport_id": 5,
    "travel_date": FUTURE.isoformat(),
    "duration_minutes": 75,
}


def _make_client(
    existing_ids: set[int] | None = None,
    unavailable: bool = False,
    timeout: bool = False,
    publisher_fails: bool = False,
) -> tuple[TestClient, FakeItineraryRepository, FakeEventPublisher]:
    """Crea un cliente con fakes inyectados y devuelve también el repo y el publisher."""
    repo = FakeItineraryRepository()
    catalog = FakeAirportCatalog(existing_ids=existing_ids, unavailable=unavailable, timeout=timeout)
    publisher = FakeEventPublisher(fail=publisher_fails)

    app.dependency_overrides[get_itinerary_repository] = lambda: repo
    app.dependency_overrides[get_airport_catalog] = lambda: catalog
    app.dependency_overrides[get_unit_of_work] = lambda: FakeUnitOfWork()
    app.dependency_overrides[get_event_publisher] = lambda: publisher

    return TestClient(app), repo, publisher


@pytest.fixture(autouse=True)
def limpiar_overrides():
    """Garantiza que los overrides se borran aunque la prueba falle."""
    yield
    app.dependency_overrides.clear()


# ── POST /itineraries ──────────────────────────────────────────────────────────

def test_crear_itinerario_devuelve_201():
    client, repo, publisher = _make_client(existing_ids={1, 5})
    response = client.post("/itineraries", json=BODY_VALIDO)

    assert response.status_code == 201
    data = response.json()
    assert data["traveler_name"] == "Ana Pérez"
    assert data["traveler_email"] is None
    assert data["duration_minutes"] == 75
    assert "id" in data
    assert len(publisher.published) == 1
    assert str(publisher.published[0].itinerary_id) == data["id"]


def test_crear_propaga_el_correlation_id_al_evento():
    """El header X-Correlation-ID de la solicitud viaja dentro del evento."""
    client, _, publisher = _make_client(existing_ids={1, 5})
    response = client.post(
        "/itineraries", json=BODY_VALIDO, headers={"X-Correlation-ID": "demo-123"}
    )

    assert response.status_code == 201
    assert publisher.published[0].correlation_id == "demo-123"


def test_crear_si_no_se_registra_el_evento_devuelve_500_sin_commit():
    """Fase 5 (ADR-026): si el evento no se registra en la outbox, no se confirma nada.

    Responde 500 INTERNAL_ERROR en formato único y nunca llega a hacer commit;
    con la base real, get_db_session deshace la transacción (rollback).
    """
    uow = FakeUnitOfWork()
    _make_client(existing_ids={1, 5}, publisher_fails=True)
    app.dependency_overrides[get_unit_of_work] = lambda: uow
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/itineraries", json=BODY_VALIDO)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert uow.commits == 0


def test_crear_con_email_devuelve_201():
    client, _, _ = _make_client(existing_ids={1, 5})
    body = {**BODY_VALIDO, "traveler_email": "ana@example.com"}
    response = client.post("/itineraries", json=body)

    assert response.status_code == 201
    assert response.json()["traveler_email"] == "ana@example.com"


def test_crear_mismos_aeropuertos_devuelve_422():
    """departure == arrival viola la regla de dominio → INVALID_ITINERARY."""
    client, _, _ = _make_client(existing_ids={1})
    body = {**BODY_VALIDO, "arrival_airport_id": 1}
    response = client.post("/itineraries", json=body)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_ITINERARY"
    assert error["details"] == {}


def test_crear_aeropuerto_salida_inexistente_devuelve_422():
    client, _, _ = _make_client(existing_ids={5})  # solo existe el de llegada
    response = client.post("/itineraries", json=BODY_VALIDO)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "AIRPORT_NOT_FOUND"
    assert error["details"]["field"] == "departure_airport_id"


def test_crear_aeropuerto_llegada_inexistente_devuelve_422():
    client, _, _ = _make_client(existing_ids={1})  # solo existe el de salida
    response = client.post("/itineraries", json=BODY_VALIDO)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "AIRPORT_NOT_FOUND"
    assert error["details"]["field"] == "arrival_airport_id"


def test_crear_airport_service_no_disponible_devuelve_503():
    client, _, _ = _make_client(unavailable=True)
    response = client.post("/itineraries", json=BODY_VALIDO)

    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "AIRPORT_SERVICE_UNAVAILABLE"
    assert error["details"] == {}


def test_crear_airport_service_timeout_devuelve_504():
    client, _, _ = _make_client(timeout=True)
    response = client.post("/itineraries", json=BODY_VALIDO)

    assert response.status_code == 504
    error = response.json()["error"]
    assert error["code"] == "AIRPORT_SERVICE_TIMEOUT"
    assert error["details"] == {}


# ── GET /itineraries ───────────────────────────────────────────────────────────

def test_listar_devuelve_lista_vacia():
    client, _, _ = _make_client()
    response = client.get("/itineraries")

    assert response.status_code == 200
    assert response.json() == []


def test_listar_devuelve_todos_los_itinerarios():
    client, _, _ = _make_client(existing_ids={1, 5})
    client.post("/itineraries", json=BODY_VALIDO)
    client.post("/itineraries", json={**BODY_VALIDO, "traveler_name": "Carlos López"})

    response = client.get("/itineraries")

    assert response.status_code == 200
    nombres = {it["traveler_name"] for it in response.json()}
    assert nombres == {"Ana Pérez", "Carlos López"}


# ── GET /itineraries/{id} ──────────────────────────────────────────────────────

def test_obtener_por_id_devuelve_200():
    client, _, _ = _make_client(existing_ids={1, 5})
    created = client.post("/itineraries", json=BODY_VALIDO).json()

    response = client.get(f"/itineraries/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_obtener_id_inexistente_devuelve_404():
    client, _, _ = _make_client()
    response = client.get(f"/itineraries/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ITINERARY_NOT_FOUND"


# ── PUT /itineraries/{id} ──────────────────────────────────────────────────────

def test_actualizar_devuelve_200_con_datos_nuevos():
    client, _, _ = _make_client(existing_ids={1, 2, 5, 6})
    created = client.post("/itineraries", json=BODY_VALIDO).json()

    body_actualizado = {
        **BODY_VALIDO,
        "traveler_name": "Ana Actualizada",
        "departure_airport_id": 2,
        "arrival_airport_id": 6,
        "duration_minutes": 120,
    }
    response = client.put(f"/itineraries/{created['id']}", json=body_actualizado)

    assert response.status_code == 200
    data = response.json()
    assert data["traveler_name"] == "Ana Actualizada"
    assert data["duration_minutes"] == 120
    assert data["id"] == created["id"]


def test_actualizar_id_inexistente_devuelve_404():
    client, _, _ = _make_client(existing_ids={1, 5})
    response = client.put(f"/itineraries/{uuid4()}", json=BODY_VALIDO)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ITINERARY_NOT_FOUND"


# ── DELETE /itineraries/{id} ───────────────────────────────────────────────────

def test_eliminar_devuelve_204():
    client, _, _ = _make_client(existing_ids={1, 5})
    created = client.post("/itineraries", json=BODY_VALIDO).json()

    response = client.delete(f"/itineraries/{created['id']}")
    assert response.status_code == 204

    assert client.get(f"/itineraries/{created['id']}").status_code == 404


def test_eliminar_id_inexistente_devuelve_404():
    client, _, _ = _make_client()
    response = client.delete(f"/itineraries/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ITINERARY_NOT_FOUND"


# ── GET /health ────────────────────────────────────────────────────────────────

def test_health_devuelve_ok():
    client, _, _ = _make_client()
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ── Manejo de errores HTTP (formato único ADR-012) ─────────────────────────────

def test_ruta_inexistente_devuelve_404_formato_unico():
    """GET a una ruta que no existe → 404 con ROUTE_NOT_FOUND en formato único."""
    client, _, _ = _make_client()
    response = client.get("/ruta-que-no-existe")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "ROUTE_NOT_FOUND"
    assert body["error"]["details"] == {}
    assert "correlation_id" in body


def test_metodo_no_permitido_devuelve_405_formato_unico():
    """DELETE /health no está definido → 405 con METHOD_NOT_ALLOWED en formato único."""
    client, _, _ = _make_client()
    response = client.delete("/health")

    assert response.status_code == 405
    body = response.json()
    assert body["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert body["error"]["details"] == {}
    assert "correlation_id" in body


def test_campo_faltante_devuelve_422_formato_unico():
    """POST sin traveler_name (campo obligatorio) → 422 con VALIDATION_ERROR en formato único."""
    client, _, _ = _make_client(existing_ids={1, 5})
    body_sin_nombre = {k: v for k, v in BODY_VALIDO.items() if k != "traveler_name"}
    response = client.post("/itineraries", json=body_sin_nombre)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "correlation_id" in body


def test_error_inesperado_devuelve_500_formato_unico():
    """Excepción no esperada en el repositorio → 500 con INTERNAL_ERROR en formato único."""

    class RepositorioRoto(ItineraryRepository):
        def save(self, it: object) -> None:
            raise RuntimeError("Error simulado")

        def get_by_id(self, itinerary_id: object) -> None:
            raise RuntimeError("Error simulado")

        def list_all(self) -> list:
            raise RuntimeError("Error simulado")

        def delete(self, itinerary_id: object) -> None:
            raise RuntimeError("Error simulado")

    app.dependency_overrides[get_itinerary_repository] = lambda: RepositorioRoto()
    app.dependency_overrides[get_airport_catalog] = lambda: FakeAirportCatalog()
    app.dependency_overrides[get_unit_of_work] = lambda: FakeUnitOfWork()
    app.dependency_overrides[get_event_publisher] = lambda: FakeEventPublisher()

    # raise_server_exceptions=False para que TestClient devuelva la respuesta 500
    # en lugar de relanzar la excepción en el lado del test.
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/itineraries")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["details"] == {}
    assert "correlation_id" in body
