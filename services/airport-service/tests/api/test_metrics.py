"""Pruebas del endpoint /metrics de Airport Service (Fase 9C, ADR-038)."""

import re

from fastapi.testclient import TestClient

from app.main import create_app


def test_metrics_devuelve_200() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/metrics")

    assert response.status_code == 200


def test_metrics_content_type_es_texto() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/metrics")

    assert response.headers["content-type"].startswith("text/plain")


def test_metrics_contiene_contadores_http() -> None:
    with TestClient(create_app()) as client:
        # Una solicitud para que el contador tenga al menos una serie
        client.get("/health")
        response = client.get("/metrics")

    body = response.text
    assert "http_requests_total" in body
    assert "http_request_duration_seconds" in body


def test_metrics_usa_plantilla_de_ruta_no_id_concreto() -> None:
    """El label `path` debe ser la plantilla (/airports/{airport_id}), no un ID numérico."""
    with TestClient(create_app()) as client:
        client.get("/airports/1")
        response = client.get("/metrics")

    body = response.text
    # La plantilla de la ruta aparece como label
    assert 'path="/airports/{airport_id}"' in body
    # El ID numérico concreto no debe aparecer como valor del label path
    assert re.search(r'path="/airports/\d+"', body) is None
