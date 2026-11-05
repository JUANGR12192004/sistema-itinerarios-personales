"""Puertos (interfaces) de la capa de aplicación de Itinerary Service.

Un puerto es un contrato que define cómo los casos de uso interactúan con
el mundo exterior (base de datos, otros servicios, mensajería). Los casos de uso
solo dependen de estos puertos, nunca de las implementaciones concretas.
Esto permite sustituir cualquier implementación sin modificar la lógica de negocio.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.application.events import ItineraryCreatedEvent
from app.domain.itinerary import Itinerary


class ItineraryRepository(ABC):
    """Puerto de acceso a la persistencia de itinerarios.

    Implementado por SqlAlchemyItineraryRepository (Fase 3) y por
    FakeItineraryRepository en las pruebas.
    """

    @abstractmethod
    def save(self, itinerary: Itinerary) -> None:
        """Guarda un itinerario nuevo o actualiza uno existente (upsert por id)."""

    @abstractmethod
    def get_by_id(self, itinerary_id: UUID) -> Itinerary | None:
        """Devuelve el itinerario o None si no existe."""

    @abstractmethod
    def list_all(self) -> list[Itinerary]:
        """Devuelve todos los itinerarios ordenados por fecha de creación."""

    @abstractmethod
    def delete(self, itinerary_id: UUID) -> None:
        """Elimina el itinerario. Si no existe, no hace nada."""


class AirportCatalog(ABC):
    """Puerto de validación de aeropuertos contra Airport Service.

    Implementado por HttpAirportCatalogAdapter (Fase 3) y por
    FakeAirportCatalog en las pruebas.

    Raises:
        AirportNotFoundInCatalogError: el aeropuerto no existe (404 de Airport Service).
        AirportServiceUnavailableError: Airport Service no está disponible (503 o error de red).
        AirportServiceTimeoutError: Airport Service tardó demasiado (504).
    """

    @abstractmethod
    def verify_exists(self, airport_id: int) -> None:
        """Verifica que el aeropuerto exista en el catálogo."""


class UnitOfWork(ABC):
    """Puerto que confirma (commit) los cambios de la transacción actual.

    Unit of Work ("unidad de trabajo") agrupa los cambios de una solicitud y los
    confirma juntos. El caso de uso lo usa para decidir CUÁNDO quedan guardados
    los datos: en la Fase 4 publica el evento solo después del commit (ADR-022).

    Implementado por SqlAlchemyUnitOfWork (Fase 4) y por FakeUnitOfWork en las pruebas.
    """

    @abstractmethod
    def commit(self) -> None:
        """Confirma en la base de datos los cambios pendientes."""


class EventPublisher(ABC):
    """Puerto de publicación de eventos de integración.

    Fase 4: RabbitMQEventPublisher (publicación directa tras el commit).
    Fase 5: adaptador Outbox (mismo puerto; el caso de uso no cambia).
    El caso de uso llama a este puerto; nunca habla directamente con RabbitMQ.

    Raises:
        EventPublishError: no se pudo publicar el evento.
    """

    @abstractmethod
    def publish(self, event: ItineraryCreatedEvent) -> None:
        """Publica el evento de integración."""
