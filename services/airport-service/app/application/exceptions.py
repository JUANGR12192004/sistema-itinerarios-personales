"""Excepciones de la capa de aplicación.

Describen fallos del proveedor de aeropuertos sin mencionar HTTP ni API Colombia.
El manejador de errores de la capa api las traduce a 502, 503 y 504.
"""


class ApplicationError(Exception):
    """Base de todas las excepciones de la capa de aplicación."""


class AirportProviderUnavailableError(ApplicationError):
    """El proveedor de aeropuertos no está disponible (sin conexión o con errores internos)."""


class AirportProviderResponseError(ApplicationError):
    """El proveedor de aeropuertos respondió algo inesperado o con un formato inválido."""


class AirportProviderTimeoutError(AirportProviderUnavailableError):
    """El proveedor de aeropuertos no respondió dentro del tiempo máximo (timeout).

    Hereda de AirportProviderUnavailableError porque también es una falta de disponibilidad:
    se reintenta, cuenta como fallo para el circuit breaker y activa el fallback igual que
    un 503. Solo cambia la respuesta HTTP final (504).
    """
