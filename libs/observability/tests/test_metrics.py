"""Pruebas del middleware de métricas HTTP (ADR-038).

Los contadores de Prometheus son globales del proceso: cada prueba compara el valor antes y
después de la solicitud en lugar de esperar un valor absoluto.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from observability.metrics import metrics_app, metrics_middleware


def build_app() -> FastAPI:
    app = FastAPI()
    app.middleware("http")(metrics_middleware)
    app.mount("/metrics", metrics_app)

    @app.get("/items/{item_id}")
    def get_item(item_id: int) -> dict:
        return {"id": item_id}

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(build_app())


def requests_total(method: str, path: str, status: str) -> float:
    labels = {"method": method, "path": path, "status": status}
    return REGISTRY.get_sample_value("http_requests_total", labels) or 0.0


def duration_count(method: str, path: str) -> float:
    labels = {"method": method, "path": path}
    return REGISTRY.get_sample_value("http_request_duration_seconds_count", labels) or 0.0


def test_cuenta_la_solicitud_con_la_plantilla_de_la_ruta(client: TestClient) -> None:
    before = requests_total("GET", "/items/{item_id}", "200")
    durations_before = duration_count("GET", "/items/{item_id}")

    client.get("/items/7")
    client.get("/items/8")

    assert requests_total("GET", "/items/{item_id}", "200") == before + 2
    assert duration_count("GET", "/items/{item_id}") == durations_before + 2
    assert requests_total("GET", "/items/7", "200") == 0


def test_registra_el_codigo_de_error(client: TestClient) -> None:
    before = requests_total("GET", "/items/{item_id}", "422")

    client.get("/items/no-es-un-numero")

    assert requests_total("GET", "/items/{item_id}", "422") == before + 1


def test_una_ruta_inexistente_usa_la_ruta_real(client: TestClient) -> None:
    before = requests_total("GET", "/no-existe", "404")

    client.get("/no-existe")

    assert requests_total("GET", "/no-existe", "404") == before + 1


def test_el_endpoint_metrics_no_se_cuenta_a_si_mismo(client: TestClient) -> None:
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert requests_total("GET", "/metrics", "200") == 0
