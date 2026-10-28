"""Pruebas de la API REST con TestClient y un proveedor falso inyectado (dependency_overrides)."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.cache_header import CACHE_HEADER
from app.api.correlation import CORRELATION_ID_HEADER
from app.api.dependencies import get_airport_provider
from app.application.exceptions import (
    AirportProviderResponseError,
    AirportProviderTimeoutError,
    AirportProviderUnavailableError,
)
from app.infrastructure.cache.cached_provider import CachedAirportProvider
from app.infrastructure.resilience.circuit_breaker import CircuitOpenError
from app.main import create_app
from tests.fakes import FakeAirportProvider, InMemoryCacheStore


@pytest.fixture
def provider() -> FakeAirportProvider:
    return FakeAirportProvider()


@pytest.fixture
def app(provider: FakeAirportProvider) -> Iterator[FastAPI]:
    application = create_app()
    application.dependency_overrides[get_airport_provider] = lambda: provider
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    # Sin "with": no se ejecuta el lifespan, así que no se crea el cliente real de API Colombia
    return TestClient(app)


def assert_error_format(body: dict[str, Any], code: str) -> None:
    """Comprueba el formato único de error (CLAUDE.md, sección 10.2)."""
    assert set(body) == {"error", "correlation_id"}
    assert set(body["error"]) == {"code", "message", "details"}
    assert body["error"]["code"] == code
    assert body["error"]["message"]
    assert body["correlation_id"]


# ---------- /health ----------


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "airport-service"}


# ---------- GET /airports ----------


def test_list_airports_returns_all_sorted(client: TestClient) -> None:
    response = client.get("/airports")

    assert response.status_code == 200
    body = response.json()
    assert [airport["id"] for airport in body] == [1, 9, 43]
    assert body[0] == {
        "id": 1,
        "name": "Aeropuerto Internacional El Edén",
        "iata_code": "AXM",
        "oaci_code": "SKAR",
        "type": "Internacional",
        "city": "Armenia",
        "department": "Quindío",
        "coordinates": {"latitude": 4.4532428642135, "longitude": -75.7659806671205},
    }


def test_airport_without_location_has_null_coordinates_and_codes(client: TestClient) -> None:
    body = client.get("/airports").json()

    cafe = next(airport for airport in body if airport["id"] == 43)
    assert cafe["coordinates"] is None
    assert cafe["iata_code"] is None
    assert cafe["oaci_code"] is None


# ---------- GET /airports/{id} ----------


def test_get_airport_by_id(client: TestClient) -> None:
    response = client.get("/airports/9")

    assert response.status_code == 200
    assert response.json()["iata_code"] == "MDE"


def test_unknown_airport_returns_404(client: TestClient) -> None:
    response = client.get("/airports/999")

    assert response.status_code == 404
    body = response.json()
    assert_error_format(body, "AIRPORT_NOT_FOUND")
    assert body["error"]["message"] == "El aeropuerto con id 999 no existe"
    assert body["error"]["details"] == {"airport_id": 999}


@pytest.mark.parametrize("invalid_id", ["0", "-1", "abc", "1.5"])
def test_invalid_id_returns_422_without_calling_the_provider(
    client: TestClient, provider: FakeAirportProvider, invalid_id: str
) -> None:
    response = client.get(f"/airports/{invalid_id}")

    assert response.status_code == 422
    body = response.json()
    assert_error_format(body, "VALIDATION_ERROR")
    assert body["error"]["details"]["errors"][0]["field"] == "airport_id"
    assert provider.calls == []  # no se consultó API Colombia


# ---------- GET /airports/map-data ----------


def test_map_data_returns_parallel_arrays_without_unlocated_airports(client: TestClient) -> None:
    response = client.get("/airports/map-data")

    assert response.status_code == 200
    assert response.json() == {
        "count": 2,
        "ids": [1, 9],
        "names": ["Aeropuerto Internacional El Edén", "Aeropuerto Internacional José María Córdova"],
        "iata_codes": ["AXM", "MDE"],
        "cities": ["Armenia", "Rionegro"],
        "departments": ["Quindío", "Antioquia"],
        "types": ["Internacional", "Internacional"],
        "latitudes": [4.4532428642135, 6.1645330006573],
        "longitudes": [-75.7659806671205, -75.423110000511],
    }


def test_map_data_is_not_confused_with_an_airport_id(client: TestClient, provider: FakeAirportProvider) -> None:
    client.get("/airports/map-data")

    assert provider.calls == ["list_airports"]


# ---------- Errores del proveedor (502 / 503 / 504) ----------


@pytest.mark.parametrize("path", ["/airports", "/airports/1", "/airports/map-data"])
@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (AirportProviderResponseError("formato inesperado"), 502, "AIRPORT_PROVIDER_BAD_RESPONSE"),
        (AirportProviderUnavailableError("sin conexión"), 503, "AIRPORT_PROVIDER_UNAVAILABLE"),
        (CircuitOpenError("circuito abierto"), 503, "AIRPORT_PROVIDER_UNAVAILABLE"),
        (AirportProviderTimeoutError("no respondió a tiempo"), 504, "AIRPORT_PROVIDER_TIMEOUT"),
    ],
)
def test_provider_errors_are_translated(
    app: FastAPI, path: str, error: Exception, status_code: int, code: str
) -> None:
    app.dependency_overrides[get_airport_provider] = lambda: FakeAirportProvider(error=error)

    response = TestClient(app).get(path)

    assert response.status_code == status_code
    assert_error_format(response.json(), code)


# ---------- Formato común y correlation ID ----------


def test_unknown_route_uses_the_error_format(client: TestClient) -> None:
    response = client.get("/no-existe")

    assert response.status_code == 404
    assert_error_format(response.json(), "ROUTE_NOT_FOUND")


def test_received_correlation_id_is_reused(client: TestClient) -> None:
    response = client.get("/airports/999", headers={CORRELATION_ID_HEADER: "prueba-123"})

    assert response.headers[CORRELATION_ID_HEADER] == "prueba-123"
    assert response.json()["correlation_id"] == "prueba-123"


def test_correlation_id_is_generated_when_missing(client: TestClient) -> None:
    response = client.get("/airports/999")

    generated = response.headers[CORRELATION_ID_HEADER]
    assert len(generated) == 36  # UUID
    assert response.json()["correlation_id"] == generated


def test_successful_responses_also_include_correlation_id(client: TestClient) -> None:
    assert CORRELATION_ID_HEADER in client.get("/airports").headers


# ---------- Header X-Cache (Fase 2) ----------


@pytest.fixture
def cached_client(app: FastAPI, provider: FakeAirportProvider) -> TestClient:
    """Cliente cuyo proveedor es el Decorator de caché real, con un almacén en memoria."""
    cached = CachedAirportProvider(
        inner=provider, store=InMemoryCacheStore(), ttl_seconds=600, stale_ttl_seconds=86400
    )
    app.dependency_overrides[get_airport_provider] = lambda: cached
    return TestClient(app)


@pytest.mark.parametrize("path", ["/airports", "/airports/1", "/airports/map-data"])
def test_cache_header_shows_miss_then_hit(
    cached_client: TestClient, provider: FakeAirportProvider, path: str
) -> None:
    first = cached_client.get(path)
    second = cached_client.get(path)

    assert first.headers[CACHE_HEADER] == "MISS"
    assert second.headers[CACHE_HEADER] == "HIT"
    assert second.json() == first.json()
    assert len(provider.calls) == 1


def test_list_and_map_data_share_the_cache(cached_client: TestClient, provider: FakeAirportProvider) -> None:
    cached_client.get("/airports")

    assert cached_client.get("/airports/map-data").headers[CACHE_HEADER] == "HIT"
    assert provider.calls == ["list_airports"]


def test_requests_without_airport_queries_have_no_cache_header(cached_client: TestClient) -> None:
    assert CACHE_HEADER not in cached_client.get("/health").headers
    assert CACHE_HEADER not in cached_client.get("/airports/0").headers  # 422: no se consultó el proveedor
