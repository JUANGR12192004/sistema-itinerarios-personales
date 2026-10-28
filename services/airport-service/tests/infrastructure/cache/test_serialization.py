"""Pruebas de la conversión de aeropuertos a JSON para la caché."""

import json

import pytest

from app.infrastructure.cache.serialization import (
    airport_from_json,
    airport_to_json,
    airports_from_json,
    airports_to_json,
)
from tests.fakes import sample_airports


def test_list_round_trip_keeps_every_field() -> None:
    airports = sample_airports()

    assert airports_from_json(airports_to_json(airports)) == airports


def test_airport_without_location_or_codes_round_trip() -> None:
    cafe = next(airport for airport in sample_airports() if airport.id == 43)

    restored = airport_from_json(airport_to_json(cafe))

    assert restored == cafe
    assert restored.coordinates is None
    assert restored.iata_code is None


def test_accents_are_stored_readable() -> None:
    assert "Quindío" in airports_to_json(sample_airports())


@pytest.mark.parametrize(
    "raw",
    [
        "no es JSON",
        json.dumps({"id": 1}),  # faltan campos
        json.dumps({**json.loads(airport_to_json(sample_airports()[0])), "id": -1}),  # viola el dominio
        json.dumps({**json.loads(airport_to_json(sample_airports()[0])), "coordinates": {"latitude": 200, "longitude": 0}}),
        json.dumps(["no", "es", "un", "aeropuerto"]),
    ],
)
def test_corrupt_airport_raises_value_error(raw: str) -> None:
    with pytest.raises(ValueError):
        airport_from_json(raw)


@pytest.mark.parametrize("raw", [json.dumps({"no": "es una lista"}), json.dumps([{"id": 1}]), "["])
def test_corrupt_list_raises_value_error(raw: str) -> None:
    with pytest.raises(ValueError):
        airports_from_json(raw)
