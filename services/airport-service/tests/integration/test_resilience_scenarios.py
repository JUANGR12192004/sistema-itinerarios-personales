"""Escenarios de la Fase 2 con la cadena real completa, de la ruta HTTP hasta API Colombia simulada.

    TestClient → rutas → casos de uso → CachedAirportProvider → ResilientAirportProvider
               → ApiColombiaAirportAdapter → ApiColombiaClient → API Colombia (respx)

Solo se reemplazan Redis (almacén en memoria), las esperas del backoff y el reloj del circuit
breaker, para que las pruebas sean rápidas y no dependan de internet ni de Redis.

Escenarios pedidos para la Fase 2:
1. La API funciona.
2. La API tarda demasiado (timeout → 504, o fallback si hay copia de respaldo).
3. La API no responde (retry, circuit breaker → 503, o fallback).
4. Consultas repetidas (caché).
"""

from collections.abc import Iterator

import httpx
import pytest
import respx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.cache_header import CACHE_HEADER
from app.api.dependencies import get_airport_provider
from app.infrastructure.api_colombia.adapter import ApiColombiaAirportAdapter
from app.infrastructure.api_colombia.client import ApiColombiaClient
from app.infrastructure.cache.cached_provider import CachedAirportProvider
from app.infrastructure.resilience.circuit_breaker import CircuitBreaker, CircuitState
from app.infrastructure.resilience.resilient_provider import ResilientAirportProvider
from app.infrastructure.resilience.retry import RetryPolicy
from app.main import create_app
from tests.fakes import FakeClock, InMemoryCacheStore, RecordingSleep
from tests.infrastructure.api_colombia.samples import BASE_URL, airport_payload

AIRPORT_URL = f"{BASE_URL}/Airport/1"
FRESH_KEY = "airport-service:v1:airport:1"


class Scenario:
    """Agrupa las piezas de la cadena para poder inspeccionarlas en cada prueba."""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self.store = InMemoryCacheStore()
        self.sleep = RecordingSleep()
        self.clock = FakeClock()
        self.breaker = CircuitBreaker(name="api-colombia", failure_threshold=3, recovery_seconds=30, clock=self.clock)
        adapter = ApiColombiaAirportAdapter(ApiColombiaClient(base_url=BASE_URL, http_client=http_client))
        resilient = ResilientAirportProvider(
            inner=adapter,
            circuit_breaker=self.breaker,
            retry_policy=RetryPolicy(max_attempts=3, base_delay=0.5, max_delay=4.0, sleep=self.sleep),
        )
        self.provider = CachedAirportProvider(
            inner=resilient, store=self.store, ttl_seconds=600, stale_ttl_seconds=86400
        )


@pytest.fixture
def scenario() -> Scenario:
    # respx intercepta las peticiones de este cliente: nunca sale a internet
    return Scenario(httpx.AsyncClient())


@pytest.fixture
def client(scenario: Scenario) -> Iterator[TestClient]:
    app: FastAPI = create_app()
    app.dependency_overrides[get_airport_provider] = lambda: scenario.provider
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------- 1. La API funciona ----------


def test_api_works(client: TestClient, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(AIRPORT_URL).respond(200, json=airport_payload())

    response = client.get("/airports/1")

    assert response.status_code == 200
    assert response.json()["coordinates"] == {"latitude": 4.4532428642135, "longitude": -75.7659806671205}
    assert response.headers[CACHE_HEADER] == "MISS"


# ---------- 2. La API tarda demasiado ----------


def test_slow_api_without_cache_returns_504_after_retries(
    client: TestClient, scenario: Scenario, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(AIRPORT_URL).mock(side_effect=httpx.ReadTimeout("tardó demasiado"))

    response = client.get("/airports/1")

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "AIRPORT_PROVIDER_TIMEOUT"
    assert route.call_count == 3  # 1 intento + 2 reintentos
    assert scenario.sleep.delays == [0.5, 1.0]  # exponential backoff


def test_slow_api_once_is_hidden_by_the_retry(
    client: TestClient, scenario: Scenario, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(AIRPORT_URL).mock(
        side_effect=[httpx.ReadTimeout("tardó demasiado"), httpx.Response(200, json=airport_payload())]
    )

    response = client.get("/airports/1")

    assert response.status_code == 200
    assert scenario.sleep.delays == [0.5]


def test_slow_api_with_stale_copy_uses_the_fallback(
    client: TestClient, scenario: Scenario, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(AIRPORT_URL)
    route.respond(200, json=airport_payload())
    original = client.get("/airports/1").json()
    scenario.store.expire(FRESH_KEY)  # pasaron los 10 minutos del dato fresco
    route.mock(side_effect=httpx.ReadTimeout("tardó demasiado"))

    response = client.get("/airports/1")

    assert response.status_code == 200
    assert response.json() == original
    assert response.headers[CACHE_HEADER] == "STALE"


# ---------- 3. La API no responde ----------


def test_down_api_returns_503_and_then_opens_the_circuit(
    client: TestClient, scenario: Scenario, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(AIRPORT_URL).mock(side_effect=httpx.ConnectError("conexión rechazada"))

    for _ in range(3):
        response = client.get("/airports/1")
        assert response.status_code == 503
    assert route.call_count == 9  # 3 consultas x 3 intentos
    assert scenario.breaker.state is CircuitState.OPEN

    # Con el circuito abierto se responde 503 al instante, sin llamar a API Colombia
    response = client.get("/airports/1")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AIRPORT_PROVIDER_UNAVAILABLE"
    assert route.call_count == 9


def test_circuit_closes_when_the_api_recovers(
    client: TestClient, scenario: Scenario, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(AIRPORT_URL).mock(side_effect=httpx.ConnectError("conexión rechazada"))
    for _ in range(3):
        client.get("/airports/1")
    assert scenario.breaker.state is CircuitState.OPEN

    scenario.clock.advance(30)  # pasa el tiempo de recuperación
    route.mock(side_effect=None)
    route.respond(200, json=airport_payload())

    response = client.get("/airports/1")

    assert response.status_code == 200
    assert scenario.breaker.state is CircuitState.CLOSED


def test_api_returning_5xx_with_stale_copy_uses_the_fallback(
    client: TestClient, scenario: Scenario, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(AIRPORT_URL)
    route.respond(200, json=airport_payload())
    client.get("/airports/1")
    scenario.store.expire(FRESH_KEY)
    route.respond(500)

    response = client.get("/airports/1")

    assert response.status_code == 200
    assert response.headers[CACHE_HEADER] == "STALE"


def test_not_found_is_not_retried_and_does_not_open_the_circuit(
    client: TestClient, scenario: Scenario, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(f"{BASE_URL}/Airport/9999").respond(404)

    for _ in range(5):
        assert client.get("/airports/9999").status_code == 404

    assert route.call_count == 5  # sin reintentos y sin caché de 404
    assert scenario.breaker.state is CircuitState.CLOSED


# ---------- 4. Consultas repetidas ----------


def test_repeated_queries_call_the_api_once(client: TestClient, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(f"{BASE_URL}/Airport").respond(200, json=[airport_payload()])

    statuses = [client.get("/airports").headers[CACHE_HEADER] for _ in range(5)]

    assert statuses == ["MISS", "HIT", "HIT", "HIT", "HIT"]
    assert route.call_count == 1


def test_redis_down_does_not_break_the_service(
    client: TestClient, scenario: Scenario, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(f"{BASE_URL}/Airport").respond(200, json=[airport_payload()])
    scenario.store.available = False

    responses = [client.get("/airports") for _ in range(2)]

    assert [response.status_code for response in responses] == [200, 200]
    assert route.call_count == 2  # sin caché cada consulta va a API Colombia
