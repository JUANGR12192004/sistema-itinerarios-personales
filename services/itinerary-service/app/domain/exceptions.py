"""Excepciones del dominio de Itinerary Service.

No dependen de HTTP: el manejador de errores de la capa api (entrega 3D)
las traduce al código HTTP y al formato único de errores.
"""


class DomainError(Exception):
    """Base de todas las excepciones del dominio."""


class InvalidItineraryError(DomainError):
    """Violación de una regla de negocio del dominio de itinerarios."""
