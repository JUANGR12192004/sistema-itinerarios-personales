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
        coordinates=_to_coordinates(dto.id, dto.latitude, dto.longitude),
    )


def _normalize_code(code: str | None) -> str | None:
    """Devuelve el código limpio, o None si falta ("N/A", vacío o nulo)."""
    if code is None:
        return None
    cleaned = code.strip()
    if not cleaned or cleaned.upper() == NOT_AVAILABLE_CODE:
        return None
    return cleaned


def _is_colombian_latitude(value: float) -> bool:
    return COLOMBIA_MIN_LATITUDE <= value <= COLOMBIA_MAX_LATITUDE


def _to_coordinates(airport_id: int, latitude: float, longitude: float) -> Coordinates | None:
    """Construye las coordenadas corrigiendo el intercambio solo cuando se detecta."""
    if latitude == 0 and longitude == 0:
        return None

    if not _is_colombian_latitude(latitude) and _is_colombian_latitude(longitude):
        logger.warning(
            "Coordenadas intercambiadas en el aeropuerto %s (latitude=%s, longitude=%s): se corrigen",
            airport_id,
            latitude,
            longitude,
        )
        latitude, longitude = longitude, latitude

    return Coordinates(latitude=latitude, longitude=longitude)
