"""Puertos (interfaces) de la capa de aplicación de Itinerary Service.

Un puerto es un contrato que define cómo los casos de uso interactúan con
el mundo exterior (base de datos, otros servicios, mensajería). Los casos de uso
solo dependen de estos puertos, nunca de las implementaciones concretas.
Esto permite sustituir cualquier implementación sin modificar la lógica de negocio.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.application.events import ItineraryCreatedEvent
from app.application.outbox import OutboxMessage
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
    los datos: en la Fase 5 confirma el itinerario y su evento en el mismo commit (ADR-026).

    Implementado por SqlAlchemyUnitOfWork (Fase 4) y por FakeUnitOfWork en las pruebas.
    """

    @abstractmethod
    def commit(self) -> None:
        """Confirma en la base de datos los cambios pendientes."""


class EventPublisher(ABC):
    """Puerto de publicación de eventos de integración.

    Adaptadores (ADR-026):
    - OutboxEventPublisher: lo usa CreateItineraryUseCase. Registra el evento en
      `outbox_events` dentro de la transacción actual; por eso el caso de uso lo
      llama ANTES del commit.
    - RabbitMQEventPublisher: lo usa el Outbox Relay (Fase 5B) para enviar a RabbitMQ
      los eventos pendientes.
    El caso de uso llama a este puerto; nunca habla directamente con RabbitMQ.

    Raises:
        EventPublishError: no se pudo publicar el evento.
    """

    @abstractmethod
    def publish(self, event: ItineraryCreatedEvent) -> None:
        """Publica el evento de integración (o lo registra para publicarlo)."""


class OutboxRepository(ABC):
    """Puerto de lectura y marcado de los mensajes de la outbox (ADR-025).

    Lo usa el Outbox Relay. Implementado por SqlAlchemyOutboxRepository y por
    FakeOutboxRepository en las pruebas. Los cambios se confirman con UnitOfWork.
    """

    @abstractmethod
    def get_pending(self, limit: int) -> list[OutboxMessage]:
        """Devuelve hasta `limit` mensajes pendientes, los más antiguos primero.

        Los mensajes quedan bloqueados para este relay hasta el commit; los que
        otro relay ya bloqueó se saltan (no se espera por ellos).
        """

    @abstractmethod
    def mark_published(self, message_id: UUID, published_at: datetime) -> None:
        """Marca el mensaje como publicado: deja de estar pendiente."""

    @abstractmethod
    def mark_failed(self, message_id: UUID, error: str) -> None:
        """Suma un intento fallido y guarda el error; el mensaje sigue pendiente."""
