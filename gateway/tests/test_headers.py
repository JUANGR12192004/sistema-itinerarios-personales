"""Headers: Authorization (preparación de JWT), X-Correlation-ID y datos del cliente original."""

import re

import httpx
import pytest

from tests.echo_server import SERVICE_CORRELATION_ID
from tests.gateway_containers import RunningGateway

GENERATED_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _received_headers(response: httpx.Response) -> dict[str, str]:
    """Headers que recibió el servicio (el eco los devuelve en el cuerpo)."""
    return response.json()["headers"]


def test_authorization_is_forwarded_unchanged(client: httpx.Client) -> None:
    token = "Bearer eyJhbGciOiJIUzI1NiJ9.prueba.firma"

    response = client.get("/api/airports/1", headers={"Authorization": token})

    assert _received_headers(response)["authorization"] == token


def test_no_authorization_is_added_when_the_client_sends_none(client: httpx.Client) -> None:
    response = client.get("/api/itineraries")

    assert "authorization" not in _received_headers(response)


def test_valid_correlation_id_is_forwarded_and_returned_once(client: httpx.Client) -> None:
    response = client.get("/api/airports/1", headers={"X-Correlation-ID": "demo-7b_001.a"})

    assert _received_headers(response)["x-correlation-id"] == "demo-7b_001.a"
    # El eco responde con su propio X-Correlation-ID: el gateway lo oculta y deja solo el suyo.
    assert response.headers.get_list("x-correlation-id") == ["demo-7b_001.a"]
    assert SERVICE_CORRELATION_ID not in response.headers.get_list("x-correlation-id")


def test_missing_correlation_id_is_generated_by_the_gateway(client: httpx.Client) -> None:
    response = client.get("/api/airports/1")

    generated = response.headers["x-correlation-id"]
    assert GENERATED_ID.match(generated)
    assert _received_headers(response)["x-correlation-id"] == generated


def test_each_request_gets_a_different_generated_id(client: httpx.Client) -> None:
    first = client.get("/api/airports/1").headers["x-correlation-id"]
    second = client.get("/api/airports/1").headers["x-correlation-id"]

    assert first != second


@pytest.mark.parametrize(
    "invalid_id",
    ['abc"def', "con espacios", '{"inyectado":true}', "x" * 129, "a/b"],
)
def test_invalid_correlation_id_is_replaced(client: httpx.Client, invalid_id: str) -> None:
    response = client.get("/api/airports/1", headers={"X-Correlation-ID": invalid_id})

    returned = response.headers["x-correlation-id"]
    assert returned != invalid_id
    assert GENERATED_ID.match(returned)
    assert _received_headers(response)["x-correlation-id"] == returned


def test_client_data_is_forwarded(client: httpx.Client, gateway: RunningGateway) -> None:
    response = client.get("/api/airports/1")

    received = _received_headers(response)
    assert received["host"] == gateway.base_url.removeprefix("http://")
    assert received["x-forwarded-proto"] == "http"
    assert received["x-real-ip"]
    assert received["x-forwarded-for"]
