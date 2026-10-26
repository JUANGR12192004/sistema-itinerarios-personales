"""Excepciones de la capa de aplicación.

Describen fallos del proveedor de aeropuertos sin mencionar HTTP ni API Colombia.
El manejador de errores de la capa api (entrega 1C) las traduce a 502 y 503.
"""


class ApplicationError(Exception):
    """Base de todas las excepciones de la capa de aplicación."""


class AirportProviderUnavailableError(ApplicationError):
    """El proveedor de aeropuertos no está disponible (sin conexión o con errores internos)."""


class AirportProviderResponseError(ApplicationError):
    """El proveedor de aeropuertos respondió algo inesperado o con un formato inválido."""
