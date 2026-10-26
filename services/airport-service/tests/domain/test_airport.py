"""Pruebas de la entidad Airport y de las excepciones del dominio."""

import dataclasses
from typing import Any

import pytest

from app.domain import Airport, AirportNotFoundError, Coordinates, DomainError, InvalidAirportError


def build_airport(**overrides: Any) -> Airport:
    """Crea un aeropuerto válido (El Edén, Armenia) y permite cambiar campos."""
    data: dict[str, Any] = {
        "id": 1,
        "name": "Aeropuerto Internacional El Edén",
        "iata_code": "AXM",
        "oaci_code": "SKAR",
        "type": "Internacional",
        "city": "Armenia",
        "department": "Quindío",
        "coordinates": Coordinates(latitude=4.4532428642135, longitude=-75.7659806671205),
    }
    data.update(overrides)
    return Airport(**data)


def test_creates_valid_airport() -> None:
    airport = build_airport()

    assert airport.id == 1
    assert airport.iata_code == "AXM"
    assert airport.city == "Armenia"
    assert airport.has_location is True


def test_airport_without_codes_is_valid() -> None:
    # Caso real: "Base Aérea BG. Arturo Lema Posada" no tiene códigos IATA ni OACI
    airport = build_airport(iata_code=None, oaci_code=None, type="Militar")

    assert airport.iata_code is None
    assert airport.oaci_code is None


def test_airport_without_coordinates_has_no_location() -> None:
    # Caso real: "Aeropuerto del Café" (en construcción) no tiene ubicación conocida
    airport = build_airport(coordinates=None)

    assert airport.has_location is False


@pytest.mark.parametrize("airport_id", [0, -1])
def test_rejects_non_positive_id(airport_id: int) -> None:
    with pytest.raises(InvalidAirportError):
        build_airport(id=airport_id)


@pytest.mark.parametrize("field_name", ["name", "type", "city", "department"])
@pytest.mark.parametrize("empty_value", ["", "   "])
def test_rejects_empty_required_text(field_name: str, empty_value: str) -> None:
    with pytest.raises(InvalidAirportError):
        build_airport(**{field_name: empty_value})


def test_airport_is_immutable() -> None:
    airport = build_airport()

    with pytest.raises(dataclasses.FrozenInstanceError):
        airport.name = "Otro nombre"  # type: ignore[misc]


def test_airport_not_found_error_keeps_id_and_message() -> None:
    error = AirportNotFoundError(999)

    assert error.airport_id == 999
    assert str(error) == "El aeropuerto con id 999 no existe"
    assert isinstance(error, DomainError)
