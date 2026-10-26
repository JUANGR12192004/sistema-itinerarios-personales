"""Entidad Airport (solo lectura)."""

from dataclasses import dataclass

from app.domain.coordinates import Coordinates
from app.domain.exceptions import InvalidAirportError


@dataclass(frozen=True)
class Airport:
    """Aeropuerto del catálogo, expresado en el modelo interno.

    - iata_code y oaci_code son None cuando el aeropuerto no tiene código.
    - coordinates es None cuando la ubicación es desconocida.
    Es inmutable porque el servicio solo consulta aeropuertos, nunca los modifica.
    """

    id: int
    name: str
    iata_code: str | None
    oaci_code: str | None
    type: str
    city: str
    department: str
    coordinates: Coordinates | None

    def __post_init__(self) -> None:
        if self.id <= 0:
            raise InvalidAirportError(f"El id del aeropuerto debe ser positivo, se recibió {self.id}")
        for field_name in ("name", "type", "city", "department"):
            if not getattr(self, field_name).strip():
                raise InvalidAirportError(f"El campo '{field_name}' del aeropuerto no puede estar vacío")

    @property
    def has_location(self) -> bool:
        """Indica si el aeropuerto se puede ubicar en un mapa."""
        return self.coordinates is not None
