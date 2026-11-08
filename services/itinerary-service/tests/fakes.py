"""Implementaciones falsas de los puertos, para usar en pruebas unitarias y de API.

Cada fake implementa el puerto correspondiente con una lógica mínima en memoria.
No dependen de PostgreSQL, de Airport Service ni de RabbitMQ.
"""

from uuid import UUID

from app.application.events import ItineraryCreatedEvent
from app.application.exceptions import (
    AirportNotFoundInCatalogError,
    AirportServiceTimeoutError,
    AirportServiceUnavailableError,
    EventPublishError,
)
from app.application.ports import (
    AirportCatalog,
    EventPublisher,
    ItineraryRepository,
    UnitOfWork,
)
from app.domain.itinerary import Itinerary


class FakeItineraryRepository(ItineraryRepository):
    """Repositorio en memoria. Comportamiento idéntico al contrato del puerto.

    `calls` es una lista opcional compartida con FakeUnitOfWork y FakeEventPublisher
    para verificar el ORDEN de las operaciones (guardar → registrar evento → commit).
    """

    def __init__(self, calls: list[str] | None = None) -> None:
        self._store: dict[UUID, Itinerary] = {}
        self._calls = calls if calls is not None else []

    def save(self, itinerary: Itinerary) -> None:
        self._calls.append("save")
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


class FakeUnitOfWork(UnitOfWork):
    """Unidad de trabajo en memoria: cuenta los commits y los anota en `calls`.

    `calls` es una lista opcional compartida con los demás fakes para verificar
    el ORDEN de las operaciones (el commit va después de registrar el evento).
    """

    def __init__(self, calls: list[str] | None = None) -> None:
        self.commits = 0
        self._calls = calls if calls is not None else []

    def commit(self) -> None:
        self.commits += 1
        self._calls.append("commit")


class FakeEventPublisher(EventPublisher):
    """Publisher que guarda los eventos en memoria para verificarlos en pruebas.

    - fail: simula que el evento no se pudo registrar ni publicar (lanza EventPublishError).
    - calls: lista compartida con los demás fakes para verificar el orden.
    """

    def __init__(self, fail: bool = False, calls: list[str] | None = None) -> None:
        self.published: list[ItineraryCreatedEvent] = []
        self._fail = fail
        self._calls = calls if calls is not None else []

    def publish(self, event: ItineraryCreatedEvent) -> None:
        self._calls.append("publish")
        if self._fail:
            raise EventPublishError("RabbitMQ no disponible (simulado)")
        self.published.append(event)
