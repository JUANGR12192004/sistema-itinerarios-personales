"""Enrutamiento: cada ruta pública llega al servicio correcto, sin el prefijo /api."""

from collections.abc import Callable

import httpx
import pytest

from tests.gateway_containers import RunningGateway


def test_health_answers_without_calling_services(client: httpx.Client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"status": "ok", "service": "api-gateway"}
    assert response.headers["x-correlation-id"]


def test_root_is_reserved_for_the_frontend(client: httpx.Client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "Fase 8" in response.text


@pytest.mark.parametrize(
    ("public_path", "service", "internal_path"),
    [
        ("/api/airports", "airport-echo", "/airports"),
        ("/api/airports/5", "airport-echo", "/airports/5"),
        ("/api/airports/map-data", "airport-echo", "/airports/map-data"),
        ("/api/airports/5?lang=es", "airport-echo", "/airports/5?lang=es"),
        ("/api/itineraries", "itinerary-echo", "/itineraries"),
        ("/api/itineraries/3f2a9c1e-6b7d-4c2a-9e1f-0a1b2c3d4e5f", "itinerary-echo",
         "/itineraries/3f2a9c1e-6b7d-4c2a-9e1f-0a1b2c3d4e5f"),
    ],
)
def test_routes_reach_the_right_service_without_api_prefix(
    client: httpx.Client, public_path: str, service: str, internal_path: str
) -> None:
    response = client.get(public_path)

    assert response.status_code == 200
    echo = response.json()
    assert echo["service"] == service
    assert echo["path"] == internal_path


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/itineraries"),
        ("PUT", "/api/itineraries/3f2a9c1e-6b7d-4c2a-9e1f-0a1b2c3d4e5f"),
        ("DELETE", "/api/itineraries/3f2a9c1e-6b7d-4c2a-9e1f-0a1b2c3d4e5f"),
    ],
)
def test_method_and_body_reach_the_service(client: httpx.Client, method: str, path: str) -> None:
    body = b'{"traveler_name": "Ana"}'

    response = client.request(method, path, content=body, headers={"Content-Type": "application/json"})

    echo = response.json()
    assert echo["method"] == method
    assert echo["body_length"] == len(body)
    assert echo["headers"]["content-type"] == "application/json"


@pytest.mark.parametrize("path", ["/api/foo", "/api/airportsX", "/api/itineraries-x", "/api", "/otra"])
def test_unknown_routes_get_route_not_found(
    client: httpx.Client,
    assert_gateway_error: Callable[[httpx.Response, int, str], dict],
    path: str,
) -> None:
    response = client.get(path)

    body = assert_gateway_error(response, 404, "ROUTE_NOT_FOUND")
    assert body["error"]["details"] is None


def test_redirect_from_a_service_points_to_the_public_route(
    client: httpx.Client, gateway: RunningGateway
) -> None:
    # El servicio redirige a /airports (ruta interna); el cliente debe recibir /api/airports.
    response = client.get("/api/airports/redirect")

    assert response.status_code == 307
    assert response.headers["location"] == f"{gateway.base_url}/api/airports"
