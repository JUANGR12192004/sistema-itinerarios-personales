"""Mapper: traduce el DTO de API Colombia a la entidad Airport del dominio.

Aquí se concentran las correcciones de los defectos del proveedor:
- Los códigos faltantes llegan como "N/A" y se convierten en None.
- Las coordenadas 0, 0 significan "ubicación desconocida" y se convierten en None.
- Las coordenadas pueden llegar intercambiadas: se detecta el caso y se corrige.
"""

import logging

from app.domain import Airport, Coordinates
from app.infrastructure.api_colombia.dto import ApiColombiaAirportDto

logger = logging.getLogger(__name__)

NOT_AVAILABLE_CODE = "N/A"

# Rango aproximado de latitudes del territorio colombiano (incluye San Andrés y el Amazonas)
COLOMBIA_MIN_LATITUDE = -5.0
COLOMBIA_MAX_LATITUDE = 14.0


def to_airport(dto: ApiColombiaAirportDto) -> Airport:
    """Convierte un aeropuerto externo en la entidad del dominio."""
    return Airport(
        id=dto.id,
        name=dto.name,
        iata_code=_normalize_code(dto.iata_code),
        oaci_code=_normalize_code(dto.oaci_code),
        type=dto.type,
        city=dto.city.name,
        department=dto.department.name,
        coordinates=_to_coordinates(dto),
    )


def _normalize_code(code: str | None) -> str | None:
    """Devuelve el código limpio, o None si falta ("N/A", vacío o nulo)."""
    if code is None:
        return None
    cleaned = code.strip()
    if not cleaned or cleaned.upper() == NOT_AVAILABLE_CODE:
        return None
    return cleaned


def has_swapped_coordinates(dto: ApiColombiaAirportDto) -> bool:
    """Indica si el aeropuerto llegó con las coordenadas intercambiadas.

    Se detecta cuando "latitude" está fuera del rango de latitudes de Colombia
    y "longitude" sí está dentro. Las coordenadas 0, 0 no cuentan (ubicación desconocida).
    """
    if _is_unknown_location(dto.latitude, dto.longitude):
        return False
    return not _is_colombian_latitude(dto.latitude) and _is_colombian_latitude(dto.longitude)


def _is_colombian_latitude(value: float) -> bool:
    return COLOMBIA_MIN_LATITUDE <= value <= COLOMBIA_MAX_LATITUDE


def _is_unknown_location(latitude: float, longitude: float) -> bool:
    return latitude == 0 and longitude == 0


def _to_coordinates(dto: ApiColombiaAirportDto) -> Coordinates | None:
    """Construye las coordenadas corrigiendo el intercambio solo cuando se detecta.

    Cada corrección se registra en DEBUG; el Adapter registra un único WARNING
    con el total de correcciones de cada respuesta.
    """
    if _is_unknown_location(dto.latitude, dto.longitude):
        return None

    if has_swapped_coordinates(dto):
        logger.debug(
            "Coordenadas intercambiadas en el aeropuerto %s (latitude=%s, longitude=%s): se corrigen",
            dto.id,
            dto.latitude,
            dto.longitude,
        )
        return Coordinates(latitude=dto.longitude, longitude=dto.latitude)

    return Coordinates(latitude=dto.latitude, longitude=dto.longitude)
