"""Casos de uso de Airport Service.

En el patrón Adapter son el "Client": dependen solo del puerto AirportProvider,
nunca de API Colombia. Por eso en las pruebas se les puede inyectar un proveedor falso.
"""

from app.application.ports import AirportProvider
from app.domain import Airport


class ListAirports:
    """Lista todos los aeropuertos del catálogo, ordenados por id."""

    def __init__(self, provider: AirportProvider) -> None:
        self._provider = provider

    async def execute(self) -> list[Airport]:
        airports = await self._provider.list_airports()
        return sorted(airports, key=lambda airport: airport.id)


class GetAirportById:
    """Obtiene un aeropuerto por su id (lanza AirportNotFoundError si no existe)."""

    def __init__(self, provider: AirportProvider) -> None:
        self._provider = provider

    async def execute(self, airport_id: int) -> Airport:
        return await self._provider.get_airport_by_id(airport_id)


class GetAirportMapData:
    """Obtiene los aeropuertos que se pueden dibujar en un mapa (los que tienen coordenadas)."""

    def __init__(self, provider: AirportProvider) -> None:
        self._provider = provider

    async def execute(self) -> list[Airport]:
        airports = await self._provider.list_airports()
        return sorted((airport for airport in airports if airport.has_location), key=lambda airport: airport.id)
