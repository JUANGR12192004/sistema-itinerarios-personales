"""Punto de entrada de Airport Service.

Aquí se "ensambla" la arquitectura hexagonal (composition root): se crean las piezas
concretas y se conectan al puerto AirportProvider que usan los casos de uso.

Desde la Fase 2, el proveedor es una cadena de Decorators que implementan el mismo puerto:

    CachedAirportProvider          caché en Redis + fallback con datos de respaldo
      └─ ResilientAirportProvider  circuit breaker + retry con exponential backoff
           └─ ApiColombiaAirportAdapter → ApiColombiaClient (httpx con timeout) → API Colombia

Ejecutar desde services/airport-service:
    uvicorn app.main:app --port 8001
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from redis.asyncio import Redis

from app.api.cache_header import cache_status_middleware
from app.api.correlation import correlation_id_middleware
from app.api.errors import register_error_handlers
from app.api.routes import airports_router, health_router
from app.application.ports import AirportProvider
from app.config import Settings, get_settings
from app.infrastructure.api_colombia.adapter import ApiColombiaAirportAdapter
from app.infrastructure.api_colombia.client import ApiColombiaClient
from app.infrastructure.cache.cached_provider import CachedAirportProvider
from app.infrastructure.cache.store import RedisCacheStore
from app.infrastructure.resilience.circuit_breaker import CircuitBreaker
from app.infrastructure.resilience.resilient_provider import ResilientAirportProvider
from app.infrastructure.resilience.retry import RetryPolicy
from app.logging_config import configure_logging


def build_airport_provider(settings: Settings, http_client: httpx.AsyncClient, redis: Redis) -> AirportProvider:
    """Construye la cadena de Decorators alrededor del Adapter de API Colombia."""
    adapter = ApiColombiaAirportAdapter(
        ApiColombiaClient(base_url=settings.api_colombia_base_url, http_client=http_client)
    )
    resilient = ResilientAirportProvider(
        inner=adapter,
        circuit_breaker=CircuitBreaker(
            name="api-colombia",
            failure_threshold=settings.circuit_breaker_failure_threshold,
            recovery_seconds=settings.circuit_breaker_recovery_seconds,
        ),
        retry_policy=RetryPolicy(
            max_attempts=settings.retry_max_attempts,
            base_delay=settings.retry_base_delay_seconds,
            max_delay=settings.retry_max_delay_seconds,
        ),
    )
    return CachedAirportProvider(
        inner=resilient,
        store=RedisCacheStore(redis),
        ttl_seconds=settings.cache_ttl_seconds,
        stale_ttl_seconds=settings.cache_stale_ttl_seconds,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Crea la aplicación FastAPI con sus rutas, errores y dependencias."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Al arrancar: un único cliente HTTP y un único cliente de Redis, reutilizados por todas las
        # solicitudes. Crear el cliente de Redis no lo conecta: si Redis no está, el servicio arranca
        # igual y funciona sin caché.
        redis = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=settings.redis_timeout_seconds,
            socket_timeout=settings.redis_timeout_seconds,
        )
        async with httpx.AsyncClient(timeout=settings.api_colombia_timeout_seconds) as http_client:
            app.state.airport_provider = build_airport_provider(settings, http_client, redis)
            yield
        # Al detener: el "async with" cierra el cliente HTTP; aquí se cierra la conexión con Redis.
        await redis.aclose()

    app = FastAPI(
        title="Airport Service",
        description=(
            "Catálogo de aeropuertos colombianos. Consulta API Colombia mediante un Adapter, "
            "con caché en Redis, timeout, retry con exponential backoff, circuit breaker y fallback."
        ),
        version="2.0.0",
        lifespan=lifespan,
    )
    app.middleware("http")(cache_status_middleware)
    app.middleware("http")(correlation_id_middleware)
    register_error_handlers(app)
    app.include_router(airports_router)
    app.include_router(health_router)
    return app


app = create_app()
