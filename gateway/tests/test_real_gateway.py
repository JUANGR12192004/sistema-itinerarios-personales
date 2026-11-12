"""Pruebas "smoke" contra el gateway REAL (el que se ejecuta en el puerto 8000 para las demostraciones).

Solo hacen solicitudes GET (no crean, cambian ni borran datos) y son pocas, para no gastar el
límite de solicitudes. Se omiten si el gateway real no está corriendo, y cada una se omite si su
servicio está apagado (el gateway responde 502). La URL se cambia con la variable GATEWAY_URL.
"""

import os
from collections.abc import Iterator

import httpx
import pytest

REAL_GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")
HTTP_TIMEOUT_SECONDS = 5.0
HEALTH_TIMEOUT_SECONDS = 1.0


@pytest.fixture(scope="module")
def real_gateway() -> Iterator[httpx.Client]:
    try:
        health = httpx.get(f"{REAL_GATEWAY_URL}/health", timeout=HEALTH_TIMEOUT_SECONDS)
        is_gateway = health.status_code == 200 and health.json().get("service") == "api-gateway"
    except (httpx.HTTPError, ValueError):
        is_gateway = False
    if not is_gateway:
        pytest.skip(f"El gateway real no está corriendo en {REAL_GATEWAY_URL} — omitiendo pruebas smoke")
    with httpx.Client(base_url=REAL_GATEWAY_URL, timeout=HTTP_TIMEOUT_SECONDS) as client:
        yield client


def _skip_if_service_down(response: httpx.Response, service: str) -> None:
    if response.status_code == 502 and response.json()["error"]["code"] == "UPSTREAM_UNAVAILABLE":
        pytest.skip(f"{service} no está corriendo — omitiendo prueba smoke")


def test_real_gateway_routes_to_airport_service(real_gateway: httpx.Client) -> None:
    response = real_gateway.get("/api/airports/5", headers={"X-Correlation-ID": "smoke-airport"})
    _skip_if_service_down(response, "Airport Service")

    assert response.status_code == 200
    assert response.json()["id"] == 5
    assert response.headers.get_list("x-correlation-id") == ["smoke-airport"]


def test_real_gateway_routes_to_itinerary_service(real_gateway: httpx.Client) -> None:
    response = real_gateway.get("/api/itineraries")
    _skip_if_service_down(response, "Itinerary Service")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_real_gateway_answers_unknown_routes(real_gateway: httpx.Client) -> None:
    response = real_gateway.get("/api/no-existe")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ROUTE_NOT_FOUND"
