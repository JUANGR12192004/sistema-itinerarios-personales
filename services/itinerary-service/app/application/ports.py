"""Puertos (interfaces) de la capa de aplicación de Itinerary Service.

Un puerto es un contrato que define cómo los casos de uso interactúan con
el mundo exterior (base de datos, otros servicios, mensajería). Los casos de uso
solo dependen de estos puertos, nunca de las implementaciones concretas.
Esto permite sustituir cualquier implementación sin modificar la lógica de negocio.
"""

from abc import ABC, abstractmethod
from uuid import UUID

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


class EventPublisher(ABC):
    """Puerto de publicación de eventos de integración.

    Se implementará en la Fase 4 con RabbitMQ y en la Fase 5 con el Outbox.
    El caso de uso llama a este puerto; nunca habla directamente con RabbitMQ.
    """

    @abstractmethod
    def publish_itinerary_created(self, itinerary: Itinerary) -> None:
        """Publica el evento ItineraryCreatedEvent."""
