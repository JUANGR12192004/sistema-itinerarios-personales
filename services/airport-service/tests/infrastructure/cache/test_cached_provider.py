"""Pruebas de CachedAirportProvider (caché + fallback) con un almacén en memoria en lugar de Redis."""

import logging

import pytest

from app.application.exceptions import (
    AirportProviderResponseError,
    AirportProviderTimeoutError,
    AirportProviderUnavailableError,
)
from app.domain import AirportNotFoundError
from app.infrastructure.cache.cached_provider import CachedAirportProvider
from app.infrastructure.cache.status import CacheStatus, start_tracking
from app.infrastructure.resilience.circuit_breaker import CircuitOpenError
from tests.fakes import FakeAirportProvider, InMemoryCacheStore

pytestmark = pytest.mark.anyio

LIST_KEY = "airport-service:v1:airports"
AIRPORT_9_KEY = "airport-service:v1:airport:9"


@pytest.fixture
def inner() -> FakeAirportProvider:
    return FakeAirportProvider()


@pytest.fixture
def store() -> InMemoryCacheStore:
    return InMemoryCacheStore()


@pytest.fixture
def provider(inner: FakeAirportProvider, store: InMemoryCacheStore) -> CachedAirportProvider:
    return CachedAirportProvider(inner=inner, store=store, ttl_seconds=600, stale_ttl_seconds=86400)


# ---------- Caché ----------


async def test_first_query_calls_the_provider_and_stores_both_copies(
    provider: CachedAirportProvider, inner: FakeAirportProvider, store: InMemoryCacheStore
) -> None:
    airports = await provider.list_airports()

    assert len(airports) == 3
    assert inner.calls == ["list_airports"]
    assert store.ttls == {LIST_KEY: 600, f"{LIST_KEY}:stale": 86400}


async def test_repeated_queries_are_served_from_the_cache(
    provider: CachedAirportProvider, inner: FakeAirportProvider
) -> None:
    first = await provider.list_airports()
    second = await provider.list_airports()

    assert second == first
    assert inner.calls == ["list_airports"]  # API Colombia se consultó una sola vez


async def test_airports_by_id_are_cached_separately(
    provider: CachedAirportProvider, inner: FakeAirportProvider, store: InMemoryCacheStore
) -> None:
    await provider.get_airport_by_id(9)
    airport = await provider.get_airport_by_id(9)

    assert airport.iata_code == "MDE"
    assert inner.calls == ["get_airport_by_id:9"]
    assert AIRPORT_9_KEY in store.data


async def test_expired_entry_is_loaded_again(
    provider: CachedAirportProvider, inner: FakeAirportProvider, store: InMemoryCacheStore
) -> None:
    await provider.list_airports()
    store.expire(LIST_KEY)

    await provider.list_airports()

    assert inner.calls == ["list_airports", "list_airports"]


async def test_not_found_is_not_cached(
    provider: CachedAirportProvider, inner: FakeAirportProvider, store: InMemoryCacheStore
) -> None:
    for _ in range(2):
        with pytest.raises(AirportNotFoundError):
            await provider.get_airport_by_id(999)

    assert inner.calls == ["get_airport_by_id:999", "get_airport_by_id:999"]
    assert store.data == {}


async def test_corrupt_entry_is_ignored_and_reloaded(
    provider: CachedAirportProvider, inner: FakeAirportProvider, store: InMemoryCacheStore
) -> None:
    store.data[LIST_KEY] = "{dato corrupto"

    airports = await provider.list_airports()

    assert len(airports) == 3
    assert inner.calls == ["list_airports"]
    assert store.data[LIST_KEY] != "{dato corrupto"  # se reemplazó por el dato bueno


# ---------- Fallback ----------


@pytest.mark.parametrize(
    "error",
    [
        AirportProviderUnavailableError("sin conexión"),
        AirportProviderTimeoutError("lento"),
        CircuitOpenError("circuito abierto"),
    ],
)
async def test_fallback_returns_stale_data_when_the_provider_is_unavailable(
    provider: CachedAirportProvider,
    inner: FakeAirportProvider,
    store: InMemoryCacheStore,
    error: Exception,
    caplog: pytest.LogCaptureFixture,
) -> None:
    original = await provider.list_airports()
    store.expire(LIST_KEY)  # el dato fresco venció, queda la copia de respaldo
    inner.error = error

    with caplog.at_level(logging.WARNING):
        airports = await provider.list_airports()

    assert airports == original
    assert "Fallback" in caplog.text


async def test_without_stale_copy_the_error_is_propagated(
    provider: CachedAirportProvider, inner: FakeAirportProvider
) -> None:
    inner.error = AirportProviderTimeoutError("lento")

    with pytest.raises(AirportProviderTimeoutError):
        await provider.get_airport_by_id(9)


async def test_bad_response_does_not_use_the_fallback(
    provider: CachedAirportProvider, inner: FakeAirportProvider, store: InMemoryCacheStore
) -> None:
    await provider.list_airports()
    store.expire(LIST_KEY)
    inner.error = AirportProviderResponseError("formato inesperado")

    with pytest.raises(AirportProviderResponseError):
        await provider.list_airports()


# ---------- Redis no disponible ----------


async def test_service_keeps_working_when_redis_is_down(
    provider: CachedAirportProvider,
    inner: FakeAirportProvider,
    store: InMemoryCacheStore,
    caplog: pytest.LogCaptureFixture,
) -> None:
    store.available = False

    with caplog.at_level(logging.WARNING):
        first = await provider.list_airports()
        second = await provider.list_airports()

    assert first == second
    assert inner.calls == ["list_airports", "list_airports"]  # sin caché, pero sin errores
    assert "Caché no disponible" in caplog.text


async def test_redis_down_and_provider_down_returns_the_provider_error(
    provider: CachedAirportProvider, inner: FakeAirportProvider, store: InMemoryCacheStore
) -> None:
    store.available = False
    inner.error = AirportProviderUnavailableError("sin conexión")

    with pytest.raises(AirportProviderUnavailableError):
        await provider.list_airports()


# ---------- Estado para el header X-Cache ----------


async def test_records_miss_hit_and_stale(
    provider: CachedAirportProvider, inner: FakeAirportProvider, store: InMemoryCacheStore
) -> None:
    statuses = start_tracking()

    await provider.list_airports()
    await provider.list_airports()
    store.expire(LIST_KEY)
    inner.error = AirportProviderUnavailableError("sin conexión")
    await provider.list_airports()

    assert statuses == [CacheStatus.MISS, CacheStatus.HIT, CacheStatus.STALE]
