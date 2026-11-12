"""Servicio de archivos estáticos del frontend (Fase 8, ADR-033)."""

from collections.abc import Callable

import httpx


def test_root_serves_html(client: httpx.Client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<!DOCTYPE html" in response.text


def test_css_served_with_correct_content_type(client: httpx.Client) -> None:
    response = client.get("/css/style.css")

    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]


def test_js_served_with_correct_content_type(client: httpx.Client) -> None:
    response = client.get("/js/main.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_nonexistent_file_returns_route_not_found_json(
    client: httpx.Client,
    assert_gateway_error: Callable[[httpx.Response, int, str], dict],
) -> None:
    response = client.get("/no-existe.html")

    body = assert_gateway_error(response, 404, "ROUTE_NOT_FOUND")
    assert body["error"]["details"] is None


def test_api_routes_not_shadowed_by_static_files(client: httpx.Client) -> None:
    response = client.get("/api/airports")

    assert response.status_code == 200
    assert "text/html" not in response.headers.get("content-type", "")
    echo = response.json()
    assert echo["service"] == "airport-echo"
