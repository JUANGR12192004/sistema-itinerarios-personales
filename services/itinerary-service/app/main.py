"""Punto de entrada de Itinerary Service."""

import logging
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from app.api.error_handler import add_error_handlers
from app.api.routes import router
from app.config import get_settings
from observability.logging_config import configure_logging, set_correlation_id
from observability.metrics import metrics_app, metrics_middleware
from observability.tracing import setup_tracing

settings = get_settings()
configure_logging(settings.log_level, settings.service_name)
setup_tracing(settings.service_name, instrumentors=["fastapi", "httpx", "sqlalchemy", "pika"])
logger = logging.getLogger(__name__)

CORRELATION_ID_HEADER = "X-Correlation-ID"
_MAX_CID_LENGTH = 128


async def _correlation_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Establece el correlation ID en el estado de la solicitud y en el ContextVar de logs."""
    received = request.headers.get(CORRELATION_ID_HEADER, "").strip()
    correlation_id = received[:_MAX_CID_LENGTH] or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    set_correlation_id(correlation_id)
    response = await call_next(request)
    response.headers[CORRELATION_ID_HEADER] = correlation_id
    return response


app = FastAPI(
    title="Itinerary Service",
    description="Gestión de itinerarios de viaje entre aeropuertos colombianos.",
    version="1.0.0",
)

app.middleware("http")(_correlation_id_middleware)
app.middleware("http")(metrics_middleware)
add_error_handlers(app)
app.include_router(router)
# Monta el endpoint /metrics que Prometheus consulta (ADR-038)
app.mount("/metrics", metrics_app)


@app.get("/health", tags=["Salud"])
def health() -> dict:
    return {"status": "ok", "service": settings.service_name}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
