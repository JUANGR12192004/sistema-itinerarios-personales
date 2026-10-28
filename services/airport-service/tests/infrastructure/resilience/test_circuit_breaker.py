"""Pruebas del CircuitBreaker. El tiempo se controla con FakeClock (no hay esperas reales)."""

import pytest

from app.application.exceptions import (
    AirportProviderResponseError,
    AirportProviderTimeoutError,
    AirportProviderUnavailableError,
)
from app.domain import Airport, AirportNotFoundError
from app.infrastructure.resilience.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState
from tests.fakes import FakeAirportProvider, FakeClock

pytestmark = pytest.mark.anyio


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def breaker(clock: FakeClock) -> CircuitBreaker:
    return CircuitBreaker(name="api-colombia", failure_threshold=3, recovery_seconds=30, clock=clock)


async def fail(breaker: CircuitBreaker, times: int, error: Exception | None = None) -> None:
    """Hace fallar al proveedor varias veces seguidas a través del circuit breaker."""
    provider = FakeAirportProvider(error=error or AirportProviderUnavailableError("caído"))
    for _ in range(times):
        with pytest.raises(type(provider.error)):  # type: ignore[arg-type]
            await breaker.call(provider.list_airports)


async def test_starts_closed_and_lets_calls_through(breaker: CircuitBreaker) -> None:
    provider = FakeAirportProvider()

    assert len(await breaker.call(provider.list_airports)) == 3
    assert breaker.state is CircuitState.CLOSED


async def test_opens_after_the_failure_threshold(breaker: CircuitBreaker) -> None:
    await fail(breaker, 2)
    assert breaker.state is CircuitState.CLOSED

    await fail(breaker, 1)
    assert breaker.state is CircuitState.OPEN


async def test_timeouts_also_count_as_failures(breaker: CircuitBreaker) -> None:
    await fail(breaker, 3, AirportProviderTimeoutError("lento"))

    assert breaker.state is CircuitState.OPEN


async def test_open_circuit_rejects_without_calling_the_provider(breaker: CircuitBreaker) -> None:
    await fail(breaker, 3)
    provider = FakeAirportProvider()

    with pytest.raises(CircuitOpenError):
        await breaker.call(provider.list_airports)

    assert provider.calls == []


def test_circuit_open_error_is_an_unavailability_error() -> None:
    # Así el manejador de errores lo traduce a 503 y el caché puede aplicar el fallback
    assert issubclass(CircuitOpenError, AirportProviderUnavailableError)


async def test_success_resets_the_consecutive_failures(breaker: CircuitBreaker) -> None:
    await fail(breaker, 2)
    await breaker.call(FakeAirportProvider().list_airports)
    await fail(breaker, 2)

    assert breaker.state is CircuitState.CLOSED


@pytest.mark.parametrize("error", [AirportNotFoundError(999), AirportProviderResponseError("formato")])
async def test_provider_answers_do_not_open_the_circuit(breaker: CircuitBreaker, error: Exception) -> None:
    # Un 404 o un 502 significan que el proveedor sí respondió
    await fail(breaker, 5, error)

    assert breaker.state is CircuitState.CLOSED


async def test_becomes_half_open_after_the_recovery_time(breaker: CircuitBreaker, clock: FakeClock) -> None:
    await fail(breaker, 3)

    clock.advance(29)
    assert breaker.state is CircuitState.OPEN
    clock.advance(1)
    assert breaker.state is CircuitState.HALF_OPEN


async def test_successful_trial_call_closes_the_circuit(breaker: CircuitBreaker, clock: FakeClock) -> None:
    await fail(breaker, 3)
    clock.advance(30)
    provider = FakeAirportProvider()

    await breaker.call(provider.list_airports)

    assert provider.calls == ["list_airports"]
    assert breaker.state is CircuitState.CLOSED


async def test_failed_trial_call_opens_the_circuit_again(breaker: CircuitBreaker, clock: FakeClock) -> None:
    await fail(breaker, 3)
    clock.advance(30)

    await fail(breaker, 1)  # basta un fallo en HALF_OPEN

    assert breaker.state is CircuitState.OPEN
    clock.advance(29)
    assert breaker.state is CircuitState.OPEN  # vuelve a esperar el tiempo completo


async def test_not_found_during_the_trial_closes_the_circuit(breaker: CircuitBreaker, clock: FakeClock) -> None:
    await fail(breaker, 3)
    clock.advance(30)

    with pytest.raises(AirportNotFoundError):
        await breaker.call(lambda: FakeAirportProvider().get_airport_by_id(999))

    assert breaker.state is CircuitState.CLOSED


async def test_only_one_trial_call_at_a_time(breaker: CircuitBreaker, clock: FakeClock) -> None:
    await fail(breaker, 3)
    clock.advance(30)
    rejected: list[Exception] = []
    provider = FakeAirportProvider()

    async def trial_call() -> list[Airport]:
        # Mientras la llamada de prueba está en curso, llega otra solicitud
        try:
            await breaker.call(provider.list_airports)
        except CircuitOpenError as error:
            rejected.append(error)
        return await provider.list_airports()

    await breaker.call(trial_call)

    assert len(rejected) == 1
    assert breaker.state is CircuitState.CLOSED


def test_zero_threshold_is_rejected() -> None:
    with pytest.raises(ValueError):
        CircuitBreaker(name="x", failure_threshold=0, recovery_seconds=30)
