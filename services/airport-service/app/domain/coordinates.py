"""Objeto de valor Coordinates."""

from dataclasses import dataclass

from app.domain.exceptions import InvalidCoordinatesError

MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0


@dataclass(frozen=True)
class Coordinates:
    """Posición geográfica ya validada.

    Es un objeto de valor: no tiene identidad propia, dos coordenadas con la
    misma latitud y longitud son iguales, y es inmutable (frozen).
    """

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not MIN_LATITUDE <= self.latitude <= MAX_LATITUDE:
            raise InvalidCoordinatesError(
                f"La latitud {self.latitude} debe estar entre {MIN_LATITUDE} y {MAX_LATITUDE}"
            )
        if not MIN_LONGITUDE <= self.longitude <= MAX_LONGITUDE:
            raise InvalidCoordinatesError(
                f"La longitud {self.longitude} debe estar entre {MIN_LONGITUDE} y {MAX_LONGITUDE}"
            )
