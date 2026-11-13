"""Headers: Authorization (preparación de JWT), X-Correlation-ID y datos del cliente original."""

import re

import httpx
import pytest

from tests.echo_server import SERVICE_CORRELATION_ID
from tests.gateway_containers import RunningGateway

GENERATED_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
# Formato W3C: 00-{32hex}-{16hex}-{2hex}
TRACEPARENT_RE = re.compile(r"^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$")


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


def test_traceparent_is_injected_to_upstream(client: httpx.Client) -> None:
    """El gateway inyecta un traceparent W3C al servicio destino (ADR-036)."""
    response = client.get("/api/airports/1")

    received = _received_headers(response)
    assert "traceparent" in received, "ngx_otel_module debe inyectar traceparent al upstream"
    assert TRACEPARENT_RE.match(received["traceparent"]), f"Formato W3C inválido: {received['traceparent']}"


def test_client_traceparent_propagates_same_trace_id(client: httpx.Client) -> None:
    """Cuando el cliente envía traceparent, el gateway preserva el trace ID (ADR-036).

    otel_trace_context=propagate crea un span hijo del cliente: mismo trace ID,
    nuevo span ID. No reenvía el traceparent original del cliente (que sería incorrecto).
    """
    client_trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    client_traceparent = f"00-{client_trace_id}-00f067aa0ba902b7-01"

    response = client.get("/api/airports/1", headers={"traceparent": client_traceparent})

    received = _received_headers(response)
    assert "traceparent" in received
    forwarded = received["traceparent"]
    assert TRACEPARENT_RE.match(forwarded), f"Formato W3C inválido: {forwarded}"
    assert client_trace_id in forwarded, "El trace ID del cliente debe conservarse en el span hijo"
