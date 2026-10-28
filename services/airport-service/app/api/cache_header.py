"""Header X-Cache: indica si la respuesta salió de la caché.

- HIT: dato fresco de Redis (no se llamó a API Colombia).
- MISS: se consultó API Colombia y el resultado se guardó en caché.
- STALE: API Colombia falló y se respondió con la copia de respaldo (fallback).
Las respuestas que no consultan aeropuertos (por ejemplo /health) no llevan el header.
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.infrastructure.cache.status import start_tracking, summarize

CACHE_HEADER = "X-Cache"


async def cache_status_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    statuses = start_tracking()
    response = await call_next(request)
    cache_status = summarize(statuses)
    if cache_status is not None:
        response.headers[CACHE_HEADER] = cache_status
    return response
