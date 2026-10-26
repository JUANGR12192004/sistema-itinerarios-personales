"""Puertos de la capa de aplicación."""

from abc import ABC, abstractmethod

from app.domain import Airport


class AirportProvider(ABC):
    """Puerto de salida para consultar aeropuertos.

    En el patrón Adapter es el "Target": la interfaz que esperan los casos de uso.
    Cualquier proveedor (API Colombia, un archivo, un proveedor falso en las pruebas)
    debe implementarla.

    Errores que puede lanzar una implementación:
    - AirportNotFoundError (dominio): el aeropuerto no existe.
    - AirportProviderUnavailableError: el proveedor no está disponible.
    - AirportProviderResponseError: el proveedor respondió algo inválido.
    """

    @abstractmethod
    async def list_airports(self) -> list[Airport]:
        """Devuelve todos los aeropuertos del catálogo."""

    @abstractmethod
    async def get_airport_by_id(self, airport_id: int) -> Airport:
        """Devuelve un aeropuerto por su id o lanza AirportNotFoundError."""
