"""Pruebas del ensamblaje de la aplicación (main.py), sin llamar a API Colombia ni a Redis."""

import logging

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.config import Settings
from app.infrastructure.api_colombia.adapter import ApiColombiaAirportAdapter
from app.infrastructure.cache.cached_provider import CachedAirportProvider
from app.infrastructure.resilience.resilient_provider import ResilientAirportProvider
from app.main import create_app


def test_startup_wires_the_decorator_chain() -> None:
    # Con "with" se ejecuta el lifespan: se crean los clientes HTTP y Redis (sin conectarse) y la cadena:
    # CachedAirportProvider → ResilientAirportProvider → ApiColombiaAirportAdapter
    with TestClient(create_app()) as client:
        provider = client.app.state.airport_provider  # type: ignore[attr-defined]

        assert isinstance(provider, CachedAirportProvider)
        assert isinstance(provider._inner, ResilientAirportProvider)
        assert isinstance(provider._inner._inner, ApiColombiaAirportAdapter)


def test_http_client_uses_the_configured_timeout() -> None:
    with TestClient(create_app(Settings(api_colombia_timeout_seconds=1.5))) as client:
        adapter = client.app.state.airport_provider._inner._inner  # type: ignore[attr-defined]

        assert adapter._client._http_client.timeout.read == 1.5


class FakeRedis:
    """Cliente de Redis falso: solo registra si se cerró la conexión."""

    def __init__(self) -> None:
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    redis = FakeRedis()
    monkeypatch.setattr(main_module.Redis, "from_url", lambda *args, **kwargs: redis)
    return redis


@pytest.mark.anyio
async def test_lifespan_closes_redis_on_normal_shutdown(fake_redis: FakeRedis) -> None:
    app = create_app()

    async with app.router.lifespan_context(app):
        assert not fake_redis.closed

    assert fake_redis.closed


@pytest.mark.anyio
async def test_lifespan_closes_redis_even_if_shutdown_is_interrupted(fake_redis: FakeRedis) -> None:
    # Si llega una excepción mientras la aplicación está en marcha (el "yield" del lifespan),
    # la conexión con Redis se cierra igual (regla S9152 de SonarCloud).
    app = create_app()

    with pytest.raises(RuntimeError):
        async with app.router.lifespan_context(app):
            raise RuntimeError("parada inesperada de prueba")

    assert fake_redis.closed


def test_logging_shows_app_warnings() -> None:
    create_app(Settings(log_level="WARNING"))

    app_logger = logging.getLogger("app")
    assert app_logger.isEnabledFor(logging.WARNING)
    assert app_logger.handlers  # tiene a dónde escribir en la consola


def test_swagger_documents_the_endpoints() -> None:
    paths = TestClient(create_app()).get("/openapi.json").json()["paths"]

    assert {"/airports", "/airports/map-data", "/airports/{airport_id}", "/health"} <= set(paths)


def test_swagger_documents_the_timeout_response() -> None:
    paths = TestClient(create_app()).get("/openapi.json").json()["paths"]

    assert "504" in paths["/airports/{airport_id}"]["get"]["responses"]
