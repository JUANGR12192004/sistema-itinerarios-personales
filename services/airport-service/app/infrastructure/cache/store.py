"""Almacén de caché clave-valor.

CachedAirportProvider depende de la interfaz CacheStore y no de Redis directamente:
así las pruebas usan un almacén en memoria sin necesitar un servidor Redis.
"""

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class CacheError(Exception):
    """El almacén de caché no está disponible o falló la operación."""


class CacheStore(ABC):
    """Guarda textos con un tiempo de expiración (TTL)."""

    @abstractmethod
    async def get(self, key: str) -> str | None:
        """Devuelve el valor guardado, o None si no existe o ya expiró."""

    @abstractmethod
    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        """Guarda el valor; Redis lo borra solo al pasar ttl_seconds."""


class RedisCacheStore(CacheStore):
    """Implementa CacheStore con Redis. Traduce los errores de Redis a CacheError.

    Si Redis falla, durante retry_after_seconds no se vuelve a intentar: el almacén se comporta
    como una caché vacía. Sin esta pausa, con Redis caído cada solicitud esperaría el timeout de
    Redis en cada lectura y escritura.
    """

    def __init__(
        self, redis: Redis, retry_after_seconds: float = 30.0, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._redis = redis
        self._retry_after_seconds = retry_after_seconds
        self._clock = clock
        self._paused_until = 0.0

    async def get(self, key: str) -> str | None:
        if self._is_paused():
            return None
        try:
            value = await self._redis.get(key)
        except (RedisError, OSError) as error:
            self._pause()
            raise CacheError(f"No se pudo leer '{key}' de Redis: {error}") from error
        return None if value is None else str(value)

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        if self._is_paused():
            return
        try:
            await self._redis.set(key, value, ex=ttl_seconds)
        except (RedisError, OSError) as error:
            self._pause()
            raise CacheError(f"No se pudo guardar '{key}' en Redis: {error}") from error

    def _is_paused(self) -> bool:
        return self._clock() < self._paused_until

    def _pause(self) -> None:
        self._paused_until = self._clock() + self._retry_after_seconds
        logger.warning("Redis no disponible: se omite la caché durante %.0f s", self._retry_after_seconds)
