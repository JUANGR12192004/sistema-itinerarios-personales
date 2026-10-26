"""Capa de dominio: entidades, objetos de valor y excepciones, sin dependencias de infraestructura."""

from app.domain.airport import Airport
from app.domain.coordinates import Coordinates
from app.domain.exceptions import (
    AirportNotFoundError,
    DomainError,
    InvalidAirportError,
    InvalidCoordinatesError,
)

__all__ = [
    "Airport",
    "AirportNotFoundError",
    "Coordinates",
    "DomainError",
    "InvalidAirportError",
    "InvalidCoordinatesError",
]
