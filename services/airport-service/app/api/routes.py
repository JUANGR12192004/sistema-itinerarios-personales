"""Rutas REST de Airport Service.

Cada ruta solo: recibe la solicitud, llama al caso de uso y convierte el resultado
al esquema de respuesta. Los errores los traduce el manejador único de errors.py.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path

from app.api.dependencies import get_get_airport_by_id, get_get_airport_map_data, get_list_airports
from app.api.schemas import AirportResponse, ErrorResponse, HealthResponse, MapDataResponse
from app.application.use_cases import GetAirportById, GetAirportMapData, ListAirports
from app.config import get_settings

PROVIDER_ERRORS: dict[int | str, dict[str, Any]] = {
    502: {"model": ErrorResponse, "description": "API Colombia respondió algo inesperado"},
    503: {"model": ErrorResponse, "description": "API Colombia no está disponible o el circuito está abierto"},
    504: {"model": ErrorResponse, "description": "API Colombia no respondió a tiempo"},
}

airports_router = APIRouter(prefix="/airports", tags=["airports"])
health_router = APIRouter(tags=["health"])


@airports_router.get("", response_model=list[AirportResponse], responses=PROVIDER_ERRORS)
async def list_airports(use_case: Annotated[ListAirports, Depends(get_list_airports)]) -> list[AirportResponse]:
    """Lista todos los aeropuertos colombianos, ordenados por id."""
    airports = await use_case.execute()
    return [AirportResponse.from_domain(airport) for airport in airports]


# Debe declararse ANTES de /{airport_id}: si no, "map-data" se tomaría como un id y daría 422.
@airports_router.get("/map-data", response_model=MapDataResponse, responses=PROVIDER_ERRORS)
async def get_map_data(use_case: Annotated[GetAirportMapData, Depends(get_get_airport_map_data)]) -> MapDataResponse:
    """Devuelve los aeropuertos con coordenadas en arreglos listos para Plotly.

    Los aeropuertos sin ubicación conocida se excluyen.
    """
    airports = await use_case.execute()
    return MapDataResponse.from_domain(airports)


@airports_router.get(
    "/{airport_id}",
    response_model=AirportResponse,
    responses={
        404: {"model": ErrorResponse, "description": "El aeropuerto no existe"},
        422: {"model": ErrorResponse, "description": "El id no es un entero mayor que 0"},
        **PROVIDER_ERRORS,
    },
)
async def get_airport(
    airport_id: Annotated[int, Path(gt=0, description="Id del aeropuerto (entero mayor que 0)")],
    use_case: Annotated[GetAirportById, Depends(get_get_airport_by_id)],
) -> AirportResponse:
    """Obtiene un aeropuerto por su id."""
    airport = await use_case.execute(airport_id)
    return AirportResponse.from_domain(airport)


@health_router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Indica que el servicio está en ejecución (no consulta API Colombia)."""
    return HealthResponse(service=get_settings().service_name)
