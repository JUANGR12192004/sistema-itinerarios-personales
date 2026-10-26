"""Adapter de API Colombia.

En el patrón Adapter es el "Adapter": implementa el puerto AirportProvider (Target)
usando ApiColombiaClient y su JSON (Adaptee). Los casos de uso (Client) nunca ven
el formato de API Colombia, solo entidades Airport.
"""

import logging
from typing import Any

from pydantic import ValidationError

from app.application.exceptions import AirportProviderResponseError
from app.application.ports import AirportProvider
from app.domain import Airport, AirportNotFoundError, DomainError
from app.infrastructure.api_colombia.client import ApiColombiaClient
from app.infrastructure.api_colombia.dto import ApiColombiaAirportDto
from app.infrastructure.api_colombia.mapper import has_swapped_coordinates, to_airport

logger = logging.getLogger(__name__)


class ApiColombiaAirportAdapter(AirportProvider):
    """Implementa AirportProvider consultando API Colombia."""

    def __init__(self, client: ApiColombiaClient) -> None:
        self._client = client

    async def list_airports(self) -> list[Airport]:
        """Devuelve los aeropuertos válidos de la lista (patrón Tolerant Reader).

        Un aeropuerto inválido se omite con un warning, para que un solo dato roto
        no deje sin catálogo a todo el sistema. Es una respuesta inesperada (502) si:
        - la respuesta completa no es una lista, o
        - la lista trae aeropuertos pero ninguno es válido: eso indica que cambió
          el contrato del proveedor, no un registro defectuoso suelto.
        Una lista vacía ([]) es legítima y se devuelve vacía.
        """
        payload = await self._client.fetch_airports()
        if not isinstance(payload, list):
            raise AirportProviderResponseError("API Colombia no respondió una lista de aeropuertos")

        airports: list[Airport] = []
        swapped_count = 0
        for position, item in enumerate(payload):
            try:
                airport, was_swapped = self._to_airport(item)
            except AirportProviderResponseError as error:
                logger.warning("Se omite el aeropuerto %s de API Colombia: %s", self._describe(item, position), error)
                continue
            airports.append(airport)
            swapped_count += was_swapped

        if payload and not airports:
            raise AirportProviderResponseError(
                f"Ninguno de los {len(payload)} aeropuertos de API Colombia es válido: posible cambio de contrato"
            )
        self._log_swapped_summary(swapped_count, len(airports))
        return airports

    async def get_airport_by_id(self, airport_id: int) -> Airport:
        """Devuelve un aeropuerto; si sus datos son inválidos, es una respuesta inesperada (502)."""
        payload = await self._client.fetch_airport(airport_id)
        if payload is None:
            raise AirportNotFoundError(airport_id)
        airport, was_swapped = self._to_airport(payload)
        self._log_swapped_summary(int(was_swapped), 1)
        return airport

    @staticmethod
    def _to_airport(item: Any) -> tuple[Airport, bool]:
        """Valida el JSON de un aeropuerto contra el DTO y lo traduce al dominio.

        Devuelve el aeropuerto y si sus coordenadas llegaron intercambiadas.
        Tanto un formato inesperado como datos que violan el dominio se reportan
        como AirportProviderResponseError.
        """
        try:
            dto = ApiColombiaAirportDto.model_validate(item)
        except ValidationError as error:
            raise AirportProviderResponseError("API Colombia respondió un formato inesperado") from error
        try:
            return to_airport(dto), has_swapped_coordinates(dto)
        except DomainError as error:
            raise AirportProviderResponseError(f"API Colombia envió datos inválidos: {error}") from error

    @staticmethod
    def _log_swapped_summary(swapped_count: int, total: int) -> None:
        """Registra un único WARNING por respuesta con el total de coordenadas corregidas."""
        if swapped_count:
            logger.warning(
                "API Colombia envió coordenadas intercambiadas en %s de %s aeropuertos: se corrigieron",
                swapped_count,
                total,
            )

    @staticmethod
    def _describe(item: Any, position: int) -> str:
        """Identifica un elemento de la lista por su id o, si no lo tiene, por su posición."""
        if isinstance(item, dict) and "id" in item:
            return f"con id {item['id']}"
        return f"en la posición {position}"
