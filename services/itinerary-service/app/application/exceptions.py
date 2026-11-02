"""Excepciones de la capa de aplicación de Itinerary Service.

Representan situaciones que ocurren al ejecutar los casos de uso:
recursos no encontrados, aeropuertos inválidos y fallos de dependencias externas.
El manejador de la capa api (entrega 3D) las traduce al formato HTTP único.
"""

from uuid import UUID


class ItineraryNotFoundError(Exception):
    """El itinerario solicitado no existe."""

    def __init__(self, itinerary_id: UUID) -> None:
        self.itinerary_id = itinerary_id
        super().__init__(f"El itinerario {itinerary_id} no existe")


class AirportNotFoundInCatalogError(Exception):
    """El aeropuerto no existe según Airport Service (recibimos 404).

    El caso de uso la convierte en DepartureAirportNotFoundError o
    ArrivalAirportNotFoundError según qué aeropuerto se estaba validando.
    """

    def __init__(self, airport_id: int) -> None:
        self.airport_id = airport_id
        super().__init__(f"El aeropuerto con id {airport_id} no existe en el catálogo")


class DepartureAirportNotFoundError(Exception):
    """El aeropuerto de salida no existe en el catálogo (404 de Airport Service)."""

    def __init__(self, airport_id: int) -> None:
        self.airport_id = airport_id
        super().__init__(f"El aeropuerto de salida con id {airport_id} no existe")


class ArrivalAirportNotFoundError(Exception):
    """El aeropuerto de llegada no existe en el catálogo (404 de Airport Service)."""

    def __init__(self, airport_id: int) -> None:
        self.airport_id = airport_id
        super().__init__(f"El aeropuerto de llegada con id {airport_id} no existe")


class AirportServiceUnavailableError(Exception):
    """Airport Service no está disponible (503 o error de red)."""


class AirportServiceTimeoutError(AirportServiceUnavailableError):
    """Airport Service tardó demasiado en responder (504).

    Subclase de AirportServiceUnavailableError porque un timeout es
    una forma de no disponibilidad, pero se reporta con un código HTTP distinto.
    """
