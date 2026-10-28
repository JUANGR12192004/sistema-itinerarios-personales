"""Pruebas del ensamblaje de la aplicación (main.py), sin llamar a API Colombia ni a Redis."""

import logging

from fastapi.testclient import TestClient

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
