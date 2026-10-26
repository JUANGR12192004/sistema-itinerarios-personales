"""Respuestas de ejemplo con la forma real de API Colombia (verificada en la entrega 1A).

Se omiten los textos largos (descripciones, población) que el DTO ignora.
"""

from typing import Any

BASE_URL = "https://api-colombia.com/api/v1"


def airport_payload(**overrides: Any) -> dict[str, Any]:
    """Aeropuerto El Edén (id 1) tal como llega: con las coordenadas intercambiadas."""
    payload: dict[str, Any] = {
        "id": 1,
        "name": "Aeropuerto Internacional El Edén",
        "iataCode": "AXM",
        "oaciCode": "SKAR",
        "type": "Internacional",
        "deparmentId": 25,
        "department": {"id": 25, "name": "Quindío", "description": "Texto largo que se ignora"},
        "cityId": 885,
        "city": {"id": 885, "name": "Armenia", "population": 316926},
        "latitude": -75.7659806671205,
        "longitude": 4.4532428642135,
    }
    payload.update(overrides)
    return payload


def military_airport_payload() -> dict[str, Any]:
    """Base Aérea BG. Arturo Lema Posada (id 45): sin códigos IATA ni OACI."""
    return airport_payload(
        id=45,
        name="Base Aérea BG. Arturo Lema Posada",
        iataCode="N/A",
        oaciCode="N/A",
        type="Militar",
        deparmentId=2,
        department={"id": 2, "name": "Antioquia"},
        cityId=91,
        city={"id": 91, "name": "Rionegro"},
        latitude=-75.42037792,
        longitude=6.166336066,
    )


def unknown_location_airport_payload() -> dict[str, Any]:
    """Aeropuerto del Café (id 43): en construcción, llega con coordenadas 0, 0."""
    return airport_payload(
        id=43,
        name="Aeropuerto del Café",
        iataCode="N/A",
        oaciCode="N/A",
        type="En Construccion",
        deparmentId=6,
        department={"id": 6, "name": "Caldas"},
        cityId=150,
        city={"id": 150, "name": "Manizales"},
        latitude=0,
        longitude=0,
    )
