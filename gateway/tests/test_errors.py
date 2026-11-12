"""Errores: los del gateway salen en JSON (sección 10.2); los de los servicios pasan sin cambios."""

from collections.abc import Callable

import httpx
import pytest

from tests.echo_server import SERVICE_ERROR_CODE

ErrorCheck = Callable[[httpx.Response, int, str], dict]


def test_service_errors_pass_through_unchanged(client: httpx.Client) -> None:
    # El "servicio" responde 502 por su cuenta: el gateway NO lo cambia por UPSTREAM_UNAVAILABLE.
    response = client.get("/api/airports/status-502")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == SERVICE_ERROR_CODE


def test_slow_service_gets_upstream_timeout(client: httpx.Client, assert_gateway_error: ErrorCheck) -> None:
    # El eco tarda 3 s y el gateway de prueba espera 1 s.
    response = client.get("/api/airports/slow")

    body = assert_gateway_error(response, 504, "UPSTREAM_TIMEOUT")
    assert body["error"]["details"] == {"service": "airport-service"}
    assert response.elapsed.total_seconds() < 3


@pytest.mark.parametrize(
    ("path", "service"),
    [("/api/airports/1", "airport-service"), ("/api/itineraries", "itinerary-service")],
)
def test_service_down_gets_upstream_unavailable(
    client_without_services: httpx.Client, assert_gateway_error: ErrorCheck, path: str, service: str
) -> None:
    response = client_without_services.get(path)

    body = assert_gateway_error(response, 502, "UPSTREAM_UNAVAILABLE")
    assert body["error"]["details"] == {"service": service}


def test_payload_too_large_is_rejected_before_reaching_the_service(
    client: httpx.Client, assert_gateway_error: ErrorCheck
) -> None:
    too_large = b"x" * (1024 * 1024 + 1)  # 1 MB + 1 byte

    response = client.post("/api/itineraries", content=too_large)

    assert_gateway_error(response, 413, "PAYLOAD_TOO_LARGE")


def test_gateway_error_reuses_a_valid_client_correlation_id(
    client_without_services: httpx.Client, assert_gateway_error: ErrorCheck
) -> None:
    response = client_without_services.get("/api/airports/1", headers={"X-Correlation-ID": "demo-error-1"})

    body = assert_gateway_error(response, 502, "UPSTREAM_UNAVAILABLE")
    assert body["correlation_id"] == "demo-error-1"
