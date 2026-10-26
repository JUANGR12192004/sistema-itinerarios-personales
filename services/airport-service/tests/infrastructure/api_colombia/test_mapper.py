"""Pruebas del DTO externo y del mapper (traducción API Colombia → dominio)."""

import logging

import pytest

from typing import Any

from app.domain import Airport, Coordinates
from app.infrastructure.api_colombia.dto import ApiColombiaAirportDto
from app.infrastructure.api_colombia.mapper import to_airport
from tests.infrastructure.api_colombia.samples import (
    airport_payload,
    military_airport_payload,
    unknown_location_airport_payload,
)

MAPPER_LOGGER = "app.infrastructure.api_colombia.mapper"


def map_payload(payload: dict[str, Any]) -> Airport:
    return to_airport(ApiColombiaAirportDto.model_validate(payload))


def test_dto_reads_external_field_names() -> None:
    dto = ApiColombiaAirportDto.model_validate(airport_payload())

    assert dto.iata_code == "AXM"
    assert dto.oaci_code == "SKAR"
    assert dto.department_id == 25  # llega como "deparmentId"
    assert dto.city.name == "Armenia"


def test_maps_airport_to_domain() -> None:
    airport = map_payload(airport_payload())

    assert airport.id == 1
    assert airport.name == "Aeropuerto Internacional El Edén"
    assert airport.iata_code == "AXM"
    assert airport.oaci_code == "SKAR"
    assert airport.type == "Internacional"
    assert airport.city == "Armenia"
    assert airport.department == "Quindío"


def test_corrects_swapped_coordinates_and_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger=MAPPER_LOGGER):
        airport = map_payload(airport_payload(latitude=-75.7659806671205, longitude=4.4532428642135))

    assert airport.coordinates == Coordinates(latitude=4.4532428642135, longitude=-75.7659806671205)
    assert len(caplog.records) == 1
    assert "intercambiadas" in caplog.records[0].getMessage()


def test_keeps_correct_coordinates_without_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger=MAPPER_LOGGER):
        airport = map_payload(airport_payload(latitude=4.4532428642135, longitude=-75.7659806671205))

    assert airport.coordinates == Coordinates(latitude=4.4532428642135, longitude=-75.7659806671205)
    assert caplog.records == []


def test_zero_coordinates_mean_unknown_location(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger=MAPPER_LOGGER):
        airport = map_payload(unknown_location_airport_payload())

    assert airport.coordinates is None
    assert airport.has_location is False
    assert caplog.records == []


def test_does_not_swap_when_both_values_are_outside_colombia() -> None:
    # Solo se invierte cuando "longitude" sí parece una latitud colombiana (entre -5 y 14).
    # Aquí ninguno de los dos valores lo parece, así que se usan tal como llegan.
    airport = map_payload(airport_payload(latitude=40.4, longitude=-75.7))

    assert airport.coordinates == Coordinates(latitude=40.4, longitude=-75.7)


@pytest.mark.parametrize("missing_code", ["N/A", "n/a", "", "   ", None])
def test_missing_codes_become_none(missing_code: str | None) -> None:
    airport = map_payload(airport_payload(iataCode=missing_code, oaciCode=missing_code))

    assert airport.iata_code is None
    assert airport.oaci_code is None


def test_maps_real_military_airport_without_codes() -> None:
    airport = map_payload(military_airport_payload())

    assert airport.iata_code is None
    assert airport.oaci_code is None
    assert airport.coordinates == Coordinates(latitude=6.166336066, longitude=-75.42037792)
