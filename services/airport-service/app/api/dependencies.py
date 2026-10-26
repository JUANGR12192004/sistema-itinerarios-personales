"""Inyección de dependencias: cómo las rutas obtienen sus casos de uso.

Las rutas piden un caso de uso con Depends(...). FastAPI construye el caso de uso
con el AirportProvider guardado en app.state al arrancar (el Adapter real).
En las pruebas, get_airport_provider se reemplaza por un proveedor falso con
app.dependency_overrides, sin tocar las rutas.
"""

from typing import Annotated

from fastapi import Depends, Request

from app.application.ports import AirportProvider
from app.application.use_cases import GetAirportById, GetAirportMapData, ListAirports


def get_airport_provider(request: Request) -> AirportProvider:
    return request.app.state.airport_provider


ProviderDependency = Annotated[AirportProvider, Depends(get_airport_provider)]


def get_list_airports(provider: ProviderDependency) -> ListAirports:
    return ListAirports(provider)


def get_get_airport_by_id(provider: ProviderDependency) -> GetAirportById:
    return GetAirportById(provider)


def get_get_airport_map_data(provider: ProviderDependency) -> GetAirportMapData:
    return GetAirportMapData(provider)
