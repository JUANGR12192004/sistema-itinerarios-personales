"""Pruebas de ResilientAirportProvider: circuit breaker por fuera del retry."""

import pytest

from app.application.exceptions import AirportProviderUnavailableError
from app.domain import AirportNotFoundError
from app.infrastructure.resilience.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState
from app.infrastructure.resilience.resilient_provider import ResilientAirportProvider
from app.infrastructure.resilience.retry import RetryPolicy
from tests.fakes import FakeAirportProvider, FakeClock, RecordingSleep

pytestmark = pytest.mark.anyio


@pytest.fixture
def inner() -> FakeAirportProvider:
    return FakeAirportProvider()


@pytest.fixture
def breaker() -> CircuitBreaker:
    return CircuitBreaker(name="api-colombia", failure_threshold=2, recovery_seconds=30, clock=FakeClock())


@pytest.fixture
def provider(inner: FakeAirportProvider, breaker: CircuitBreaker) -> ResilientAirportProvider:
    retry = RetryPolicy(max_attempts=3, base_delay=0.5, max_delay=4.0, sleep=RecordingSleep())
    return ResilientAirportProvider(inner=inner, circuit_breaker=breaker, retry_policy=retry)


async def test_delegates_to_the_inner_provider(provider: ResilientAirportProvider) -> None:
    assert len(await provider.list_airports()) == 3
    assert (await provider.get_airport_by_id(9)).iata_code == "MDE"


async def test_transient_failure_is_hidden_by_the_retry(
    provider: ResilientAirportProvider, inner: FakeAirportProvider, breaker: CircuitBreaker
) -> None:
    inner.fail_next(AirportProviderUnavailableError("5xx"))

    assert (await provider.get_airport_by_id(1)).id == 1
    assert inner.calls == ["get_airport_by_id:1", "get_airport_by_id:1"]
    assert breaker.state is CircuitState.CLOSED


async def test_a_query_with_all_retries_failed_counts_as_one_circuit_failure(
    provider: ResilientAirportProvider, inner: FakeAirportProvider, breaker: CircuitBreaker
) -> None:
    inner.error = AirportProviderUnavailableError("caído")

    with pytest.raises(AirportProviderUnavailableError):
        await provider.list_airports()
    assert len(inner.calls) == 3  # 3 intentos
    assert breaker.state is CircuitState.CLOSED  # pero un solo fallo para el circuito (umbral 2)

    with pytest.raises(AirportProviderUnavailableError):
        await provider.list_airports()
    assert breaker.state is CircuitState.OPEN


async def test_open_circuit_skips_the_retries(
    provider: ResilientAirportProvider, inner: FakeAirportProvider
) -> None:
    inner.error = AirportProviderUnavailableError("caído")
    for _ in range(2):
        with pytest.raises(AirportProviderUnavailableError):
            await provider.list_airports()
    inner.calls.clear()

    with pytest.raises(CircuitOpenError):
        await provider.get_airport_by_id(1)
    assert inner.calls == []  # respuesta inmediata, sin esperar timeouts ni reintentos


async def test_not_found_is_not_retried(provider: ResilientAirportProvider, inner: FakeAirportProvider) -> None:
    with pytest.raises(AirportNotFoundError):
        await provider.get_airport_by_id(999)

    assert inner.calls == ["get_airport_by_id:999"]
