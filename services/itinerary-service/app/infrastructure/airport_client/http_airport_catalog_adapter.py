"""Adaptador HTTP que implementa el puerto AirportCatalog consultando Airport Service."""

import logging

import httpx

from app.application.exceptions import (
    AirportNotFoundInCatalogError,
    AirportServiceTimeoutError,
    AirportServiceUnavailableError,
)
from app.application.ports import AirportCatalog

logger = logging.getLogger(__name__)


class HttpAirportCatalogAdapter(AirportCatalog):
    """Implementa AirportCatalog llamando a GET /airports/{id} de Airport Service."""

    def __init__(self, base_url: str, timeout: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def verify_exists(self, airport_id: int) -> None:
        url = f"{self._base_url}/airports/{airport_id}"
        try:
            response = httpx.get(url, timeout=self._timeout)
        except httpx.TimeoutException:
            logger.warning("Timeout al consultar Airport Service para el aeropuerto %s", airport_id)
            raise AirportServiceTimeoutError(
                f"Airport Service no respondió en {self._timeout}s al verificar el aeropuerto {airport_id}"
            )
        except httpx.RequestError as exc:
            logger.warning("Error de red al consultar Airport Service: %s", exc)
            raise AirportServiceUnavailableError(
                f"No se pudo conectar con Airport Service al verificar el aeropuerto {airport_id}"
            )

        if response.status_code == 200:
            return

        if response.status_code == 404:
            raise AirportNotFoundInCatalogError(airport_id)

        if response.status_code == 504:
            logger.warning(
                "Airport Service reportó timeout interno (504) para el aeropuerto %s", airport_id
            )
            raise AirportServiceTimeoutError(
                f"Airport Service reportó timeout interno al verificar el aeropuerto {airport_id}"
            )

        logger.warning(
            "Airport Service respondió con código inesperado %s para el aeropuerto %s",
            response.status_code,
            airport_id,
        )
        raise AirportServiceUnavailableError(
            f"Airport Service respondió con código inesperado {response.status_code}"
        )
