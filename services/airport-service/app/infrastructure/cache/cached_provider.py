"""Decorator de caché para AirportProvider, con fallback de datos vencidos.

Patrón Decorator: CachedAirportProvider implementa el puerto AirportProvider y envuelve a
otro proveedor (el ResilientAirportProvider). El Adapter de API Colombia no se modifica.

Por cada consulta se guardan dos copias en el almacén:
- fresca (ttl_seconds, 10 min): mientras exista, se responde desde la caché (HIT).
- de respaldo o "stale" (stale_ttl_seconds, 24 h): solo se usa como fallback cuando el
  proveedor no está disponible (sin conexión, timeout o circuito abierto) (STALE).

Reglas:
- Un 404 (AirportNotFoundError) no se guarda: se propaga tal cual.
- Una respuesta inválida (502) no activa el fallback: el proveedor respondió, el problema no es de disponibilidad.
- Si el almacén (Redis) falla, el servicio sigue funcionando sin caché y se registra un warning.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.application.exceptions import AirportProviderUnavailableError
from app.application.ports import AirportProvider
from app.domain import Airport
from app.infrastructure.cache.serialization import (
    airport_from_json,
    airport_to_json,
    airports_from_json,
    airports_to_json,
)
from app.infrastructure.cache.status import CacheStatus, record
from app.infrastructure.cache.store import CacheError, CacheStore

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Prefijo de todas las claves. La "v1" permite invalidar la caché si cambia el formato guardado.
KEY_PREFIX = "airport-service:v1"


class CachedAirportProvider(AirportProvider):
    """Implementa AirportProvider consultando primero la caché y, si falta, al proveedor envuelto."""

    def __init__(self, inner: AirportProvider, store: CacheStore, ttl_seconds: int, stale_ttl_seconds: int) -> None:
        self._inner = inner
        self._store = store
        self._ttl_seconds = ttl_seconds
        self._stale_ttl_seconds = stale_ttl_seconds

    async def list_airports(self) -> list[Airport]:
        return await self._get_or_load("airports", self._inner.list_airports, airports_to_json, airports_from_json)

    async def get_airport_by_id(self, airport_id: int) -> Airport:
        return await self._get_or_load(
            f"airport:{airport_id}",
            lambda: self._inner.get_airport_by_id(airport_id),
            airport_to_json,
            airport_from_json,
        )

    async def _get_or_load(
        self,
        name: str,
        load: Callable[[], Awaitable[T]],
        to_json: Callable[[T], str],
        from_json: Callable[[str], T],
    ) -> T:
        fresh_key = f"{KEY_PREFIX}:{name}"
        stale_key = f"{fresh_key}:stale"

        # 1. ¿Hay un dato fresco en caché?
        cached = await self._read(fresh_key, from_json)
        if cached is not None:
            logger.debug("Caché HIT: %s", fresh_key)
            record(CacheStatus.HIT)
            return cached

        # 2. No hay: se consulta al proveedor (con circuit breaker, retry y timeout).
        try:
            value = await load()
        except AirportProviderUnavailableError as error:
            # 3. Fallback: el proveedor no está disponible; se usa la copia de respaldo si existe.
            stale = await self._read(stale_key, from_json)
            if stale is None:
                raise
            logger.warning("Fallback: se responde %s con datos de respaldo porque %s", fresh_key, error)
            record(CacheStatus.STALE)
            return stale

        # 4. Se guardan la copia fresca y la de respaldo.
        logger.debug("Caché MISS: %s", fresh_key)
        record(CacheStatus.MISS)
        serialized = to_json(value)
        await self._write(fresh_key, serialized, self._ttl_seconds)
        await self._write(stale_key, serialized, self._stale_ttl_seconds)
        return value

    async def _read(self, key: str, from_json: Callable[[str], T]) -> T | None:
        """Lee y reconstruye un valor; si Redis falla o el dato está corrupto, se trata como ausente."""
        try:
            raw = await self._store.get(key)
        except CacheError as error:
            logger.warning("Caché no disponible al leer, se continúa sin caché: %s", error)
            return None
        if raw is None:
            return None
        try:
            return from_json(raw)
        except ValueError as error:
            logger.warning("Se ignora la entrada corrupta %s de la caché: %s", key, error)
            return None

    async def _write(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            await self._store.set(key, value, ttl_seconds)
        except CacheError as error:
            logger.warning("Caché no disponible al guardar, se continúa sin caché: %s", error)
