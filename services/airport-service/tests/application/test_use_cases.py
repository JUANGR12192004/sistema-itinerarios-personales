"""Pruebas de los casos de uso con un proveedor falso (sin HTTP)."""

import pytest

from app.application.exceptions import AirportProviderUnavailableError
from app.application.use_cases import GetAirportById, GetAirportMapData, ListAirports
from app.domain import AirportNotFoundError
from tests.fakes import FakeAirportProvider

pytestmark = pytest.mark.anyio


async def test_list_airports_returns_all_sorted_by_id() -> None:
    airports = await ListAirports(FakeAirportProvider()).execute()

    assert [airport.id for airport in airports] == [1, 9, 43]


async def test_get_airport_by_id_returns_the_airport() -> None:
    airport = await GetAirportById(FakeAirportProvider()).execute(9)

    assert airport.iata_code == "MDE"


async def test_get_airport_by_id_propagates_not_found() -> None:
    with pytest.raises(AirportNotFoundError):
        await GetAirportById(FakeAirportProvider()).execute(999)


async def test_map_data_excludes_airports_without_coordinates() -> None:
    airports = await GetAirportMapData(FakeAirportProvider()).execute()

    assert [airport.id for airport in airports] == [1, 9]
    assert all(airport.has_location for airport in airports)


async def test_provider_errors_propagate_to_the_caller() -> None:
    provider = FakeAirportProvider(error=AirportProviderUnavailableError("sin conexión"))

    with pytest.raises(AirportProviderUnavailableError):
        await ListAirports(provider).execute()
