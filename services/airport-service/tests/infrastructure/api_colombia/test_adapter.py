"""Pruebas de ApiColombiaAirportAdapter: del JSON simulado de API Colombia a entidades Airport."""

import logging
from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from app.application.exceptions import AirportProviderResponseError, AirportProviderUnavailableError
from app.application.ports import AirportProvider
from app.domain import Airport, AirportNotFoundError, Coordinates
from app.infrastructure.api_colombia.adapter import ApiColombiaAirportAdapter
from app.infrastructure.api_colombia.client import ApiColombiaClient
from tests.infrastructure.api_colombia.samples import (
    BASE_URL,
    airport_payload,
    military_airport_payload,
    unknown_location_airport_payload,
)

pytestmark = pytest.mark.anyio

ADAPTER_LOGGER = "app.infrastructure.api_colombia.adapter"


@pytest.fixture
async def adapter() -> AsyncIterator[ApiColombiaAirportAdapter]:
    async with httpx.AsyncClient() as http_client:
        yield ApiColombiaAirportAdapter(ApiColombiaClient(base_url=BASE_URL, http_client=http_client))


async def test_adapter_implements_the_port(adapter: ApiColombiaAirportAdapter) -> None:
    assert isinstance(adapter, AirportProvider)


async def test_list_airports_returns_domain_entities(
    adapter: ApiColombiaAirportAdapter, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(f"{BASE_URL}/Airport").respond(
        200, json=[airport_payload(), military_airport_payload(), unknown_location_airport_payload()]
    )

    airports = await adapter.list_airports()

    assert [airport.id for airport in airports] == [1, 45, 43]
    assert all(isinstance(airport, Airport) for airport in airports)
    assert airports[0].coordinates == Coordinates(latitude=4.4532428642135, longitude=-75.7659806671205)
    assert airports[1].iata_code is None
    assert airports[2].coordinates is None


async def test_get_airport_by_id_returns_domain_entity(
    adapter: ApiColombiaAirportAdapter, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(f"{BASE_URL}/Airport/1").respond(200, json=airport_payload())

    airport = await adapter.get_airport_by_id(1)

    assert airport.id == 1
    assert airport.iata_code == "AXM"
    assert airport.city == "Armenia"
    assert airport.department == "Quindío"
    assert airport.coordinates == Coordinates(latitude=4.4532428642135, longitude=-75.7659806671205)


async def test_external_404_becomes_airport_not_found(
    adapter: ApiColombiaAirportAdapter, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(f"{BASE_URL}/Airport/9999").respond(404)

    with pytest.raises(AirportNotFoundError) as error_info:
        await adapter.get_airport_by_id(9999)

    assert error_info.value.airport_id == 9999


async def test_unavailable_provider_propagates(adapter: ApiColombiaAirportAdapter, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{BASE_URL}/Airport").mock(side_effect=httpx.ConnectError("sin conexión"))

    with pytest.raises(AirportProviderUnavailableError):
        await adapter.list_airports()


async def test_get_by_id_with_unexpected_format_is_response_error(
    adapter: ApiColombiaAirportAdapter, respx_mock: respx.MockRouter
) -> None:
    payload = airport_payload()
    del payload["name"]
    respx_mock.get(f"{BASE_URL}/Airport/1").respond(200, json=payload)

    with pytest.raises(AirportProviderResponseError):
        await adapter.get_airport_by_id(1)


async def test_get_by_id_with_data_that_breaks_domain_rules_is_response_error(
    adapter: ApiColombiaAirportAdapter, respx_mock: respx.MockRouter
) -> None:
    # El JSON tiene la forma correcta, pero el nombre vacío viola una regla del dominio
    respx_mock.get(f"{BASE_URL}/Airport/1").respond(200, json=airport_payload(name="  "))

    with pytest.raises(AirportProviderResponseError):
        await adapter.get_airport_by_id(1)


async def test_list_response_that_is_not_a_list_is_response_error(
    adapter: ApiColombiaAirportAdapter, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(f"{BASE_URL}/Airport").respond(200, json={"message": "formato distinto"})

    with pytest.raises(AirportProviderResponseError):
        await adapter.list_airports()


async def test_list_response_with_invalid_json_is_response_error(
    adapter: ApiColombiaAirportAdapter, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(f"{BASE_URL}/Airport").respond(200, text="<html>no es JSON</html>")

    with pytest.raises(AirportProviderResponseError):
        await adapter.list_airports()


async def test_list_skips_invalid_airports_and_returns_the_valid_ones(
    adapter: ApiColombiaAirportAdapter, respx_mock: respx.MockRouter, caplog: pytest.LogCaptureFixture
) -> None:
    # Tolerant Reader: los aeropuertos inválidos se omiten con un warning
    without_name = airport_payload(id=7)
    del without_name["name"]
    respx_mock.get(f"{BASE_URL}/Airport").respond(
        200,
        json=[
            airport_payload(),  # válido (id 1)
            without_name,  # formato inesperado (id 7)
            airport_payload(id=8, name="  "),  # viola el dominio (id 8)
            "no es un objeto",  # sin id: se identifica por su posición (3)
            military_airport_payload(),  # válido (id 45)
        ],
    )

    with caplog.at_level(logging.WARNING, logger=ADAPTER_LOGGER):
        airports = await adapter.list_airports()

    assert [airport.id for airport in airports] == [1, 45]
    # caplog también captura los warnings del mapper (coordenadas): se cuentan solo los del Adapter
    messages = [record.getMessage() for record in caplog.records if record.name == ADAPTER_LOGGER]
    assert len(messages) == 3
    assert "con id 7" in messages[0]
    assert "con id 8" in messages[1]
    assert "en la posición 3" in messages[2]


async def test_list_with_only_invalid_airports_is_response_error(
    adapter: ApiColombiaAirportAdapter, respx_mock: respx.MockRouter
) -> None:
    # Si ningún aeropuerto es válido, probablemente cambió el contrato del proveedor
    respx_mock.get(f"{BASE_URL}/Airport").respond(200, json=[airport_payload(name=""), {"inesperado": True}])

    with pytest.raises(AirportProviderResponseError):
        await adapter.list_airports()


async def test_empty_list_is_returned_as_empty(adapter: ApiColombiaAirportAdapter, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{BASE_URL}/Airport").respond(200, json=[])

    assert await adapter.list_airports() == []
