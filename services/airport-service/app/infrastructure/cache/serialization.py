"""Conversión de aeropuertos del dominio a JSON (para guardarlos en Redis) y de vuelta.

Al leer se reconstruyen las entidades con sus constructores, así que un dato guardado
que viole el dominio se detecta igual que si viniera del proveedor.
Cualquier dato corrupto se reporta como ValueError.
"""

import json
from typing import Any

from app.domain import Airport, Coordinates, DomainError


def airports_to_json(airports: list[Airport]) -> str:
    return json.dumps([_to_dict(airport) for airport in airports], ensure_ascii=False)


def airports_from_json(raw: str) -> list[Airport]:
    data = _load(raw)
    if not isinstance(data, list):
        raise ValueError("La caché no contiene una lista de aeropuertos")
    return [_from_dict(item) for item in data]


def airport_to_json(airport: Airport) -> str:
    return json.dumps(_to_dict(airport), ensure_ascii=False)


def airport_from_json(raw: str) -> Airport:
    return _from_dict(_load(raw))


def _load(raw: str) -> Any:
    try:
        return json.loads(raw)
    except ValueError as error:
        raise ValueError(f"La caché contiene un JSON inválido: {error}") from error


def _to_dict(airport: Airport) -> dict[str, Any]:
    coordinates = airport.coordinates
    return {
        "id": airport.id,
        "name": airport.name,
        "iata_code": airport.iata_code,
        "oaci_code": airport.oaci_code,
        "type": airport.type,
        "city": airport.city,
        "department": airport.department,
        "coordinates": (
            None if coordinates is None else {"latitude": coordinates.latitude, "longitude": coordinates.longitude}
        ),
    }


def _from_dict(data: Any) -> Airport:
    try:
        coordinates = data["coordinates"]
        return Airport(
            id=data["id"],
            name=data["name"],
            iata_code=data["iata_code"],
            oaci_code=data["oaci_code"],
            type=data["type"],
            city=data["city"],
            department=data["department"],
            coordinates=(
                None
                if coordinates is None
                else Coordinates(latitude=coordinates["latitude"], longitude=coordinates["longitude"])
            ),
        )
    except (KeyError, TypeError, AttributeError, DomainError) as error:
        raise ValueError(f"La caché contiene un aeropuerto inválido: {error!r}") from error
