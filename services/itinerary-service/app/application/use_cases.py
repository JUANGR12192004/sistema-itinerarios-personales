"""Casos de uso del servicio de itinerarios: crear, consultar, listar, actualizar y eliminar."""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.events import ItineraryCreatedEvent
from app.application.exceptions import (
    AirportNotFoundInCatalogError,
    ArrivalAirportNotFoundError,
    DepartureAirportNotFoundError,
    EventPublishError,
    ItineraryNotFoundError,
)
from app.application.ports import (
    AirportCatalog,
    EventPublisher,
    ItineraryRepository,
    UnitOfWork,
)
from app.domain.itinerary import Itinerary

logger = logging.getLogger(__name__)


@dataclass
class CreateItineraryCommand:
    traveler_name: str
    departure_airport_id: int
    arrival_airport_id: int
    travel_date: datetime
    duration_minutes: int
    traveler_email: str | None = None
    # Correlation ID de la solicitud HTTP; viaja en el evento para seguir el flujo completo
    correlation_id: str | None = None


@dataclass
class UpdateItineraryCommand:
    traveler_name: str
    departure_airport_id: int
    arrival_airport_id: int
    travel_date: datetime
    duration_minutes: int
    traveler_email: str | None = None


class CreateItineraryUseCase:
    def __init__(
        self,
        repo: ItineraryRepository,
        airport_catalog: AirportCatalog,
        unit_of_work: UnitOfWork,
        event_publisher: EventPublisher,
    ) -> None:
        self._repo = repo
        self._airport_catalog = airport_catalog
        self._unit_of_work = unit_of_work
        self._event_publisher = event_publisher

    def execute(self, command: CreateItineraryCommand) -> Itinerary:
        # AirportServiceUnavailableError y AirportServiceTimeoutError se propagan sin envolver
        try:
            self._airport_catalog.verify_exists(command.departure_airport_id)
        except AirportNotFoundInCatalogError as exc:
            raise DepartureAirportNotFoundError(exc.airport_id) from exc

        try:
            self._airport_catalog.verify_exists(command.arrival_airport_id)
        except AirportNotFoundInCatalogError as exc:
            raise ArrivalAirportNotFoundError(exc.airport_id) from exc

        itinerary = Itinerary.create(
            traveler_name=command.traveler_name,
            departure_airport_id=command.departure_airport_id,
            arrival_airport_id=command.arrival_airport_id,
            travel_date=command.travel_date,
            duration_minutes=command.duration_minutes,
            traveler_email=command.traveler_email,
        )

        # Publicación directa tras el commit (Fase 4, ADR-022):
        # 1) se guarda el itinerario, 2) se confirma la transacción, 3) se publica el evento.
        # Publicar antes del commit podría anunciar un itinerario que luego no se guarda.
        self._repo.save(itinerary)
        self._unit_of_work.commit()

        event = ItineraryCreatedEvent.from_itinerary(itinerary, command.correlation_id)
        try:
            self._event_publisher.publish(event)
        except EventPublishError:
            # El itinerario YA está guardado: se responde 201 y el evento se pierde.
            # Este es el problema de "double write" (dos escrituras sin transacción
            # común) que la Fase 5 resuelve con el Transactional Outbox.
            logger.error(
                "Evento perdido: itinerario %s guardado pero %s (event_id=%s) no se publicó",
                itinerary.id,
                event.EVENT_TYPE,
                event.event_id,
                exc_info=True,
            )

        return itinerary


class GetItineraryUseCase:
    def __init__(self, repo: ItineraryRepository) -> None:
        self._repo = repo

    def execute(self, itinerary_id: UUID) -> Itinerary:
        itinerary = self._repo.get_by_id(itinerary_id)
        if itinerary is None:
            raise ItineraryNotFoundError(itinerary_id)
        return itinerary


class ListItinerariesUseCase:
    def __init__(self, repo: ItineraryRepository) -> None:
        self._repo = repo

    def execute(self) -> list[Itinerary]:
        return self._repo.list_all()


class UpdateItineraryUseCase:
    def __init__(
        self,
        repo: ItineraryRepository,
        airport_catalog: AirportCatalog,
    ) -> None:
        self._repo = repo
        self._airport_catalog = airport_catalog

    def execute(self, itinerary_id: UUID, command: UpdateItineraryCommand) -> Itinerary:
        itinerary = self._repo.get_by_id(itinerary_id)
        if itinerary is None:
            raise ItineraryNotFoundError(itinerary_id)

        try:
            self._airport_catalog.verify_exists(command.departure_airport_id)
        except AirportNotFoundInCatalogError as exc:
            raise DepartureAirportNotFoundError(exc.airport_id) from exc

        try:
            self._airport_catalog.verify_exists(command.arrival_airport_id)
        except AirportNotFoundInCatalogError as exc:
            raise ArrivalAirportNotFoundError(exc.airport_id) from exc

        itinerary.update(
            traveler_name=command.traveler_name,
            departure_airport_id=command.departure_airport_id,
            arrival_airport_id=command.arrival_airport_id,
            travel_date=command.travel_date,
            duration_minutes=command.duration_minutes,
            traveler_email=command.traveler_email,
        )

        self._repo.save(itinerary)
        return itinerary


class DeleteItineraryUseCase:
    def __init__(self, repo: ItineraryRepository) -> None:
        self._repo = repo

    def execute(self, itinerary_id: UUID) -> None:
        if self._repo.get_by_id(itinerary_id) is None:
            raise ItineraryNotFoundError(itinerary_id)
        self._repo.delete(itinerary_id)
