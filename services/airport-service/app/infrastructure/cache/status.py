"""Estado de la caché en la solicitud actual: HIT, MISS o STALE.

CachedAirportProvider anota aquí de dónde salieron los datos, y la capa api lo publica en el
header X-Cache de la respuesta. Así el puerto AirportProvider no cambia (sigue devolviendo
solo aeropuertos) y se puede ver la caché funcionando desde curl o Swagger.

Se usa un ContextVar: una variable con un valor distinto por cada solicitud en curso.
"""

from contextvars import ContextVar
from enum import Enum


class CacheStatus(Enum):
    HIT = "HIT"  # dato fresco leído de Redis, sin llamar a API Colombia
    MISS = "MISS"  # no estaba en caché: se consultó API Colombia y se guardó
    STALE = "STALE"  # fallback: API Colombia falló y se devolvió la copia de respaldo vencida


_current_statuses: ContextVar[list[CacheStatus] | None] = ContextVar("cache_statuses", default=None)


def start_tracking() -> list[CacheStatus]:
    """Empieza a registrar los estados de la solicitud actual y devuelve la lista donde quedarán."""
    statuses: list[CacheStatus] = []
    _current_statuses.set(statuses)
    return statuses


def record(status: CacheStatus) -> None:
    """Anota un estado (no hace nada si no se está registrando, por ejemplo en pruebas unitarias)."""
    statuses = _current_statuses.get()
    if statuses is not None:
        statuses.append(status)


def summarize(statuses: list[CacheStatus]) -> str | None:
    """Resume los estados de la solicitud: el peor de ellos (STALE > MISS > HIT), o None si no hubo."""
    for status in (CacheStatus.STALE, CacheStatus.MISS, CacheStatus.HIT):
        if status in statuses:
            return status.value
    return None
