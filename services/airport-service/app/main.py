"""Punto de entrada de Airport Service.

Aquí se "ensambla" la arquitectura hexagonal (composition root): se crean las piezas
concretas (cliente HTTP, Adapter) y se conectan al puerto que usan los casos de uso.

Ejecutar desde services/airport-service:
    uvicorn app.main:app --port 8001
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api.correlation import correlation_id_middleware
from app.api.errors import register_error_handlers
from app.api.routes import airports_router, health_router
from app.config import Settings, get_settings
from app.infrastructure.api_colombia.adapter import ApiColombiaAirportAdapter
from app.infrastructure.api_colombia.client import ApiColombiaClient
from app.logging_config import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Crea la aplicación FastAPI con sus rutas, errores y dependencias."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Al arrancar: un único cliente HTTP reutilizable para todas las solicitudes.
        # En la Fase 1 se usa el timeout por defecto de httpx (5 s); en la Fase 2 será configurable.
        async with httpx.AsyncClient() as http_client:
            client = ApiColombiaClient(base_url=settings.api_colombia_base_url, http_client=http_client)
            app.state.airport_provider = ApiColombiaAirportAdapter(client)
            yield
        # Al detener: el "async with" cierra las conexiones del cliente HTTP.

    app = FastAPI(
        title="Airport Service",
        description="Catálogo de aeropuertos colombianos. Consulta API Colombia mediante un Adapter.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.middleware("http")(correlation_id_middleware)
    register_error_handlers(app)
    app.include_router(airports_router)
    app.include_router(health_router)
    return app


app = create_app()
