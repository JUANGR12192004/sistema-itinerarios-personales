"""Métricas de Prometheus para Itinerary Service (ADR-038, Fase 9C).

Registra métricas HTTP (recuento y duración) y la métrica de negocio
itineraries_created_total. El endpoint /metrics es montado en main.py.
Las métricas del Outbox Relay (proceso aparte, puerto 9101) se definen
en app/outbox_relay.py, ya que se ejecutan en un proceso diferente.
"""

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from prometheus_client import Counter, Histogram, make_asgi_app

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total de solicitudes HTTP recibidas",
    ["method", "path", "status"],
)

HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "Duración de las solicitudes HTTP en segundos",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Métrica de negocio: itinerarios creados exitosamente (ADR-038)
ITINERARIES_CREATED = Counter(
    "itineraries_created_total",
    "Total de itinerarios de viaje creados exitosamente",
)

# App ASGI que sirve el CollectorRegistry global en texto plano (formato Prometheus)
metrics_app = make_asgi_app()


async def metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Middleware que registra métricas HTTP para cada solicitud.

    Omite /metrics para no auto-instrumentar el propio endpoint de métricas.
    Lee la plantilla de la ruta (/itineraries/{itinerary_id}) después de call_next
    para evitar la explosión de cardinalidad con IDs en la URL.
    """
    if request.url.path == "/metrics":
        return await call_next(request)

    start = time.monotonic()
    response = await call_next(request)
    duration = time.monotonic() - start

    route = request.scope.get("route")
    path = route.path if route else request.url.path

    HTTP_REQUESTS.labels(method=request.method, path=path, status=str(response.status_code)).inc()
    HTTP_DURATION.labels(method=request.method, path=path).observe(duration)

    return response
