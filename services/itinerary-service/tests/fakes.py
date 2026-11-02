"""Implementaciones falsas de los puertos, para usar en pruebas unitarias y de API.

Cada fake implementa el puerto correspondiente con una lógica mínima en memoria.
No dependen de PostgreSQL, de Airport Service ni de RabbitMQ.
"""

from uuid import UUID

from app.application.exceptions import (
    AirportNotFoundInCatalogError,
    AirportServiceTimeoutError,
    AirportServiceUnavailableError,
)
from app.application.ports import AirportCatalog, EventPublisher, ItineraryRepository
from app.domain.itinerary import Itinerary


class FakeItineraryRepository(ItineraryRepository):
    """Repositorio en memoria. Comportamiento idéntico al contrato del puerto."""

    def __init__(self) -> None:
        self._store: dict[UUID, Itinerary] = {}

    def save(self, itinerary: Itinerary) -> None:
        self._store[itinerary.id] = itinerary

    def get_by_id(self, itinerary_id: UUID) -> Itinerary | None:
        return self._store.get(itinerary_id)

    def list_all(self) -> list[Itinerary]:
        return sorted(self._store.values(), key=lambda it: it.created_at)

    def delete(self, itinerary_id: UUID) -> None:
        self._store.pop(itinerary_id, None)


class FakeAirportCatalog(AirportCatalog):
    """Catálogo de aeropuertos configurable para simular distintos escenarios.

    Por defecto (sin argumentos) todos los ids existen.
    - existing_ids: conjunto de ids válidos; si se pasa, solo esos existen.
    - unavailable: simula que Airport Service responde 503 o tiene error de red.
    - timeout: simula que Airport Service no responde a tiempo (504).
    """

    def __init__(
        self,
        existing_ids: set[int] | None = None,
        unavailable: bool = False,
        timeout: bool = False,
    ) -> None:
        self._existing_ids = existing_ids
        self._unavailable = unavailable
        self._timeout = timeout

    def verify_exists(self, airport_id: int) -> None:
        if self._timeout:
            raise AirportServiceTimeoutError("Airport Service no respondió a tiempo (simulado)")
        if self._unavailable:
            raise AirportServiceUnavailableError("Airport Service no disponible (simulado)")
        if self._existing_ids is not None and airport_id not in self._existing_ids:
            raise AirportNotFoundInCatalogError(airport_id)


class FakeEventPublisher(EventPublisher):
    """Publisher que guarda los eventos en memoria para verificarlos en pruebas."""

    def __init__(self) -> None:
        self.published: list[Itinerary] = []

    def publish_itinerary_created(self, itinerary: Itinerary) -> None:
        self.published.append(itinerary)
