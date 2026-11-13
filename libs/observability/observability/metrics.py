"""Métricas HTTP de Prometheus compartidas por los servicios FastAPI (ADR-038, Fase 9C).

Expone HTTP_REQUESTS (Counter), HTTP_DURATION (Histogram), metrics_app (ASGI) y
metrics_middleware (middleware FastAPI). Usado por Airport Service e Itinerary Service.

Los contadores específicos de cada componente (itineraries_created_total,
notifications_dispatched_total y los contadores del Outbox Relay) se definen en
el módulo metrics.py del componente correspondiente.
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

# App ASGI estándar que sirve el CollectorRegistry global en texto plano (formato Prometheus)
metrics_app = make_asgi_app()


async def metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Registra métricas HTTP para cada solicitud.

    Se omite /metrics para no auto-instrumentar el propio endpoint de métricas.
    La plantilla de la ruta se lee DESPUÉS de call_next, cuando el router ya la resolvió
    y la dejó en request.scope["route"]. Usar la plantilla evita la explosión de
    cardinalidad (una serie por ID numérico en lugar de una por ruta parametrizada).
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
