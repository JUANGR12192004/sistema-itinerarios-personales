"""Pruebas de RetryPolicy (retry con exponential backoff). No hay esperas reales: se usa RecordingSleep."""

import pytest

from app.application.exceptions import (
    AirportProviderResponseError,
    AirportProviderTimeoutError,
    AirportProviderUnavailableError,
)
from app.domain import AirportNotFoundError
from app.infrastructure.resilience.retry import RetryPolicy
from tests.fakes import FakeAirportProvider, RecordingSleep

pytestmark = pytest.mark.anyio


@pytest.fixture
def sleep() -> RecordingSleep:
    return RecordingSleep()


@pytest.fixture
def retry(sleep: RecordingSleep) -> RetryPolicy:
    return RetryPolicy(max_attempts=3, base_delay=0.5, max_delay=4.0, sleep=sleep)


async def test_success_on_first_attempt_does_not_retry(retry: RetryPolicy, sleep: RecordingSleep) -> None:
    provider = FakeAirportProvider()

    airports = await retry.run(provider.list_airports)

    assert len(airports) == 3
    assert provider.calls == ["list_airports"]
    assert sleep.delays == []


async def test_transient_failure_is_retried_until_success(retry: RetryPolicy, sleep: RecordingSleep) -> None:
    provider = FakeAirportProvider()
    provider.fail_next(AirportProviderUnavailableError("5xx"), AirportProviderTimeoutError("lento"))

    airports = await retry.run(provider.list_airports)

    assert len(airports) == 3
    assert len(provider.calls) == 3
    assert sleep.delays == [0.5, 1.0]  # exponential backoff: 0.5 s y luego el doble


async def test_raises_the_last_error_when_attempts_are_exhausted(retry: RetryPolicy, sleep: RecordingSleep) -> None:
    provider = FakeAirportProvider()
    provider.fail_next(
        AirportProviderUnavailableError("1"), AirportProviderUnavailableError("2"), AirportProviderTimeoutError("3")
    )

    with pytest.raises(AirportProviderTimeoutError, match="3"):
        await retry.run(provider.list_airports)

    assert len(provider.calls) == 3
    assert sleep.delays == [0.5, 1.0]  # no se espera después del último intento


@pytest.mark.parametrize(
    "error", [AirportNotFoundError(999), AirportProviderResponseError("formato inesperado")]
)
async def test_errors_that_would_repeat_are_not_retried(
    retry: RetryPolicy, sleep: RecordingSleep, error: Exception
) -> None:
    provider = FakeAirportProvider(error=error)

    with pytest.raises(type(error)):
        await retry.run(provider.list_airports)

    assert len(provider.calls) == 1
    assert sleep.delays == []


def test_delays_grow_exponentially_up_to_the_maximum() -> None:
    retry = RetryPolicy(max_attempts=10, base_delay=0.5, max_delay=4.0)

    assert [retry.delay_before_retry(n) for n in range(1, 7)] == [0.5, 1.0, 2.0, 4.0, 4.0, 4.0]


async def test_single_attempt_means_no_retries(sleep: RecordingSleep) -> None:
    provider = FakeAirportProvider(error=AirportProviderUnavailableError("caído"))

    with pytest.raises(AirportProviderUnavailableError):
        await RetryPolicy(max_attempts=1, base_delay=0.5, max_delay=4.0, sleep=sleep).run(provider.list_airports)

    assert len(provider.calls) == 1


def test_zero_attempts_is_rejected() -> None:
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=0, base_delay=0.5, max_delay=4.0)
