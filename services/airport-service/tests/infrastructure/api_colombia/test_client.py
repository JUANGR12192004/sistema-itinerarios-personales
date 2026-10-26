"""Pruebas de ApiColombiaClient. respx simula API Colombia: no se usa internet."""

from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from app.application.exceptions import AirportProviderResponseError, AirportProviderUnavailableError
from app.infrastructure.api_colombia.client import ApiColombiaClient
from tests.infrastructure.api_colombia.samples import BASE_URL, airport_payload

pytestmark = pytest.mark.anyio


@pytest.fixture
async def client() -> AsyncIterator[ApiColombiaClient]:
    async with httpx.AsyncClient() as http_client:
        yield ApiColombiaClient(base_url=BASE_URL, http_client=http_client)


async def test_fetch_airports_returns_json_list(client: ApiColombiaClient, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{BASE_URL}/Airport").respond(200, json=[airport_payload()])

    assert await client.fetch_airports() == [airport_payload()]


async def test_fetch_airport_returns_json_object(client: ApiColombiaClient, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{BASE_URL}/Airport/1").respond(200, json=airport_payload())

    assert await client.fetch_airport(1) == airport_payload()


async def test_fetch_airport_returns_none_on_404(client: ApiColombiaClient, respx_mock: respx.MockRouter) -> None:
    # Comportamiento real verificado: ID inexistente → 404 con cuerpo vacío
    respx_mock.get(f"{BASE_URL}/Airport/9999").respond(404)

    assert await client.fetch_airport(9999) is None


async def test_base_url_with_trailing_slash_is_accepted(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(f"{BASE_URL}/Airport").respond(200, json=[])

    async with httpx.AsyncClient() as http_client:
        await ApiColombiaClient(base_url=f"{BASE_URL}/", http_client=http_client).fetch_airports()

    assert route.called


@pytest.mark.parametrize("status_code", [500, 503])
async def test_server_error_means_unavailable(
    client: ApiColombiaClient, respx_mock: respx.MockRouter, status_code: int
) -> None:
    respx_mock.get(f"{BASE_URL}/Airport").respond(status_code)

    with pytest.raises(AirportProviderUnavailableError):
        await client.fetch_airports()


@pytest.mark.parametrize("error", [httpx.ConnectError("sin conexión"), httpx.ReadTimeout("tardó demasiado")])
async def test_connection_problem_means_unavailable(
    client: ApiColombiaClient, respx_mock: respx.MockRouter, error: httpx.RequestError
) -> None:
    respx_mock.get(f"{BASE_URL}/Airport/1").mock(side_effect=error)

    with pytest.raises(AirportProviderUnavailableError):
        await client.fetch_airport(1)


async def test_unexpected_status_is_response_error(client: ApiColombiaClient, respx_mock: respx.MockRouter) -> None:
    # Comportamiento real verificado: id 0 o no numérico → 400
    respx_mock.get(f"{BASE_URL}/Airport/0").respond(400)

    with pytest.raises(AirportProviderResponseError):
        await client.fetch_airport(0)


async def test_invalid_json_is_response_error(client: ApiColombiaClient, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{BASE_URL}/Airport").respond(200, text="<html>no es JSON</html>")

    with pytest.raises(AirportProviderResponseError):
        await client.fetch_airports()
