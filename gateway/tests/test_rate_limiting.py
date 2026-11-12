"""Rate limiting por IP: 10 solicitudes por segundo con una ráfaga de 20 (valores reales).

Cada prueba usa un gateway nuevo (fixture rate_limited_gateway), así su contador empieza vacío.
Sus servicios no existen: las solicitudes aceptadas responden 502 y las rechazadas 429, porque
el límite se aplica antes de llamar al servicio.
"""

import time
from collections.abc import Callable

import httpx

ErrorCheck = Callable[[httpx.Response, int, str], dict]

BURST = 20
MAX_ATTEMPTS = 200


def _send_until_rate_limited(client: httpx.Client) -> tuple[int, httpx.Response]:
    """Envía solicitudes seguidas hasta el primer 429; devuelve cuántas se aceptaron antes y el 429."""
    for accepted in range(MAX_ATTEMPTS):
        response = client.get("/api/airports/1")
        if response.status_code == 429:
            return accepted, response
    raise AssertionError(f"Ningún 429 después de {MAX_ATTEMPTS} solicitudes seguidas")


def test_requests_over_the_limit_get_429_in_json(
    rate_limited_client: httpx.Client, assert_gateway_error: ErrorCheck
) -> None:
    accepted, rejected = _send_until_rate_limited(rate_limited_client)

    # La primera solicitud + la ráfaga completa se aceptan de inmediato (nodelay).
    assert accepted >= BURST + 1
    body = assert_gateway_error(rejected, 429, "RATE_LIMIT_EXCEEDED")
    assert body["error"]["details"] == {"retry_after_seconds": 1}
    assert rejected.headers["retry-after"] == "1"


def test_health_is_not_rate_limited(rate_limited_client: httpx.Client) -> None:
    _send_until_rate_limited(rate_limited_client)

    for _ in range(5):
        assert rate_limited_client.get("/health").status_code == 200


def test_limit_applies_to_both_services(rate_limited_client: httpx.Client) -> None:
    # El límite es por IP, no por servicio: agotarlo en /api/airports también afecta a /api/itineraries.
    _send_until_rate_limited(rate_limited_client)

    assert rate_limited_client.get("/api/itineraries").status_code == 429


def test_limit_recovers_after_waiting(rate_limited_client: httpx.Client) -> None:
    _send_until_rate_limited(rate_limited_client)

    time.sleep(1.1)  # a 10 r/s, en un segundo se liberan unas 10 solicitudes

    assert rate_limited_client.get("/api/airports/1").status_code == 502  # aceptada (no 429)
