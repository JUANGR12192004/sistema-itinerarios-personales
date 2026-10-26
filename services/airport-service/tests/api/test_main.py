"""Pruebas del ensamblaje de la aplicación (main.py), sin llamar a API Colombia."""

import logging

from fastapi.testclient import TestClient

from app.config import Settings
from app.infrastructure.api_colombia.adapter import ApiColombiaAirportAdapter
from app.main import create_app


def test_startup_wires_the_api_colombia_adapter() -> None:
    # Con "with" se ejecuta el lifespan: se crea el cliente HTTP y el Adapter real
    with TestClient(create_app()) as client:
        assert isinstance(client.app.state.airport_provider, ApiColombiaAirportAdapter)  # type: ignore[attr-defined]


def test_logging_shows_app_warnings() -> None:
    create_app(Settings(log_level="WARNING"))

    app_logger = logging.getLogger("app")
    assert app_logger.isEnabledFor(logging.WARNING)
    assert app_logger.handlers  # tiene a dónde escribir en la consola


def test_swagger_documents_the_endpoints() -> None:
    paths = TestClient(create_app()).get("/openapi.json").json()["paths"]

    assert {"/airports", "/airports/map-data", "/airports/{airport_id}", "/health"} <= set(paths)
