"""Pruebas de RedisCacheStore con un Redis simulado (no se necesita un servidor Redis)."""

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.infrastructure.cache.store import CacheError, RedisCacheStore
from tests.fakes import FakeClock

pytestmark = pytest.mark.anyio


class StubRedis:
    """Imita los métodos get y set de redis.asyncio.Redis que usa RedisCacheStore."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.data: dict[str, str] = {}
        self.expirations: dict[str, int] = {}
        self.calls = 0

    async def get(self, key: str) -> str | None:
        self.calls += 1
        if self.error:
            raise self.error
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int) -> bool:
        self.calls += 1
        if self.error:
            raise self.error
        self.data[key] = value
        self.expirations[key] = ex
        return True


async def test_set_stores_the_value_with_its_ttl() -> None:
    redis = StubRedis()
    store = RedisCacheStore(redis)  # type: ignore[arg-type]

    await store.set("clave", "valor", ttl_seconds=600)

    assert redis.data == {"clave": "valor"}
    assert redis.expirations == {"clave": 600}
    assert await store.get("clave") == "valor"


async def test_missing_key_returns_none() -> None:
    assert await RedisCacheStore(StubRedis()).get("no-existe") is None  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "error", [RedisConnectionError("Redis caído"), RedisTimeoutError("Redis lento"), OSError("socket cerrado")]
)
@pytest.mark.parametrize("operation", ["get", "set"])
async def test_redis_errors_become_cache_errors(error: Exception, operation: str) -> None:
    store = RedisCacheStore(StubRedis(error=error))  # type: ignore[arg-type]

    with pytest.raises(CacheError):
        if operation == "get":
            await store.get("clave")
        else:
            await store.set("clave", "valor", ttl_seconds=600)


async def test_after_a_failure_redis_is_skipped_for_a_while() -> None:
    redis = StubRedis(error=RedisConnectionError("Redis caído"))
    clock = FakeClock()
    store = RedisCacheStore(redis, retry_after_seconds=30, clock=clock)  # type: ignore[arg-type]
    with pytest.raises(CacheError):
        await store.get("clave")

    # Durante la pausa se comporta como caché vacía, sin esperar el timeout de Redis
    assert await store.get("clave") is None
    await store.set("clave", "valor", ttl_seconds=600)
    assert redis.calls == 1

    # Pasada la pausa vuelve a intentar con Redis
    redis.error = None
    clock.advance(30)
    await store.set("clave", "valor", ttl_seconds=600)
    assert await store.get("clave") == "valor"
