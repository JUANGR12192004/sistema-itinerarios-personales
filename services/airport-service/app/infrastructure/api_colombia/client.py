"""Cliente HTTP de API Colombia.

En el patrón Adapter forma parte del "Adaptee": habla el idioma del proveedor
(URLs, códigos HTTP, JSON) y no conoce el dominio. Solo traduce los fallos de
transporte a las excepciones de la capa de aplicación.
"""

import logging
from typing import Any

import httpx

from app.application.exceptions import (
    AirportProviderResponseError,
    AirportProviderTimeoutError,
    AirportProviderUnavailableError,
)

logger = logging.getLogger(__name__)


class ApiColombiaClient:
    """Hace las peticiones HTTP a los recursos /Airport de API Colombia."""

    def __init__(self, base_url: str, http_client: httpx.AsyncClient) -> None:
        self._base_url = base_url.rstrip("/")
        self._http_client = http_client

    async def fetch_airports(self) -> Any:
        """Devuelve el JSON de GET /Airport (una lista de aeropuertos)."""
        response = await self._get("/Airport")
        return self._parse_json(response)

    async def fetch_airport(self, airport_id: int) -> Any | None:
        """Devuelve el JSON de GET /Airport/{id}, o None si API Colombia responde 404."""
        response = await self._get(f"/Airport/{airport_id}")
        if response.status_code == httpx.codes.NOT_FOUND:
            return None
        return self._parse_json(response)

    async def _get(self, path: str) -> httpx.Response:
        url = f"{self._base_url}{path}"
        try:
            return await self._http_client.get(url)
        except httpx.TimeoutException as error:
            # El tiempo máximo lo define el httpx.AsyncClient creado en main.py (API_COLOMBIA_TIMEOUT_SECONDS)
            logger.warning("API Colombia no respondió a tiempo en %s: %s", url, type(error).__name__)
            raise AirportProviderTimeoutError("API Colombia no respondió a tiempo") from error
        except httpx.RequestError as error:
            # Sin conexión, DNS fallido, conexión cortada, etc.
            logger.warning("No se pudo conectar con API Colombia en %s: %s", url, error)
            raise AirportProviderUnavailableError("API Colombia no está disponible") from error

    @staticmethod
    def _parse_json(response: httpx.Response) -> Any:
        if response.is_server_error:
            logger.warning("API Colombia respondió %s en %s", response.status_code, response.url)
            raise AirportProviderUnavailableError("API Colombia no está disponible")
        if response.status_code != httpx.codes.OK:
            logger.warning("API Colombia respondió un código inesperado %s en %s", response.status_code, response.url)
            raise AirportProviderResponseError(f"API Colombia respondió con el código {response.status_code}")
        try:
            return response.json()
        except ValueError as error:
            raise AirportProviderResponseError("API Colombia respondió un JSON inválido") from error
