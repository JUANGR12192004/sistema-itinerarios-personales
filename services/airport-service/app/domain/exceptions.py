"""Excepciones del dominio de Airport Service.

No dependen de HTTP: el manejador de errores de la capa api (entrega 1C)
las traduce al código HTTP y al formato único de errores.
"""


class DomainError(Exception):
    """Base de todas las excepciones del dominio."""


class InvalidCoordinatesError(DomainError):
    """La latitud o la longitud están fuera de su rango válido."""


class InvalidAirportError(DomainError):
    """Los datos de un aeropuerto no cumplen las reglas del dominio."""


class AirportNotFoundError(DomainError):
    """El aeropuerto solicitado no existe en el catálogo."""

    def __init__(self, airport_id: int) -> None:
        self.airport_id = airport_id
        super().__init__(f"El aeropuerto con id {airport_id} no existe")
