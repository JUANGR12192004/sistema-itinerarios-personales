"""Métricas de Prometheus para Airport Service (ADR-038, Fase 9C).

Registra el recuento y la duración de las solicitudes HTTP recibidas y monta
el endpoint /metrics que Prometheus consulta cada 15 s.

Las métricas se definen en este módulo (nivel de módulo = se registran una sola vez
en el CollectorRegistry global), y se usan en el middleware de main.py.
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
    """Middleware que registra métricas HTTP para cada solicitud.

    Se omite /metrics para no auto-instrumentar el propio endpoint de métricas.
    La plantilla de la ruta (/airports/{id}) se lee DESPUÉS de call_next, que es
    cuando el router ya resolvió la ruta y la dejó en request.scope["route"].
    Usar la plantilla evita la explosión de cardinalidad (una serie por ID numérico).
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
