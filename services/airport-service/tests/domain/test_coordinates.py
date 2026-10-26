"""Pruebas del objeto de valor Coordinates."""

import dataclasses

import pytest

from app.domain import Coordinates, InvalidCoordinatesError


def test_creates_valid_coordinates() -> None:
    # Aeropuerto El Edén (Armenia), con las coordenadas ya corregidas
    coordinates = Coordinates(latitude=4.4532428642135, longitude=-75.7659806671205)

    assert coordinates.latitude == 4.4532428642135
    assert coordinates.longitude == -75.7659806671205


@pytest.mark.parametrize("latitude", [-90.0, 90.0])
def test_accepts_latitude_limits(latitude: float) -> None:
    assert Coordinates(latitude=latitude, longitude=0.0).latitude == latitude


@pytest.mark.parametrize("longitude", [-180.0, 180.0])
def test_accepts_longitude_limits(longitude: float) -> None:
    assert Coordinates(latitude=0.0, longitude=longitude).longitude == longitude


@pytest.mark.parametrize("latitude", [-90.1, 90.1])
def test_rejects_latitude_out_of_range(latitude: float) -> None:
    with pytest.raises(InvalidCoordinatesError):
        Coordinates(latitude=latitude, longitude=0.0)


def test_range_validation_cannot_detect_swapped_values() -> None:
    # API Colombia envía las coordenadas intercambiadas (latitude=-75.76, longitude=4.45).
    # Ambos valores están dentro de los rangos válidos, así que el dominio no puede detectarlo:
    # la corrección le corresponde al mapper del Adapter (entrega 1B).
    swapped = Coordinates(latitude=-75.7659806671205, longitude=4.4532428642135)

    assert swapped.latitude == -75.7659806671205


@pytest.mark.parametrize("longitude", [-180.1, 180.1])
def test_rejects_longitude_out_of_range(longitude: float) -> None:
    with pytest.raises(InvalidCoordinatesError):
        Coordinates(latitude=0.0, longitude=longitude)


def test_coordinates_with_same_values_are_equal() -> None:
    assert Coordinates(4.45, -75.76) == Coordinates(4.45, -75.76)


def test_coordinates_are_immutable() -> None:
    coordinates = Coordinates(4.45, -75.76)

    with pytest.raises(dataclasses.FrozenInstanceError):
        coordinates.latitude = 10.0  # type: ignore[misc]
