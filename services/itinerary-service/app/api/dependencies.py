"""Factories de dependencias FastAPI para inyectar los puertos en las rutas."""

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.ports import (
    AirportCatalog,
    EventPublisher,
    ItineraryRepository,
    UnitOfWork,
)
from app.config import get_settings
from app.infrastructure.airport_client.http_airport_catalog_adapter import (
    HttpAirportCatalogAdapter,
)
from app.infrastructure.persistence.database import get_session_factory
from app.infrastructure.persistence.outbox_event_publisher import OutboxEventPublisher
from app.infrastructure.persistence.repository import SqlAlchemyItineraryRepository
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


def get_db_session() -> Generator[Session, None, None]:
    """Sesión SQLAlchemy con commit automático al salir sin error y rollback si hay excepción."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_itinerary_repository(
    session: Session = Depends(get_db_session),
) -> ItineraryRepository:
    return SqlAlchemyItineraryRepository(session)


def get_unit_of_work(
    session: Session = Depends(get_db_session),
) -> UnitOfWork:
    # FastAPI reutiliza get_db_session dentro de la misma solicitud:
    # el repositorio y la unidad de trabajo comparten la misma sesión.
    return SqlAlchemyUnitOfWork(session)


def get_airport_catalog() -> AirportCatalog:
    settings = get_settings()
    return HttpAirportCatalogAdapter(
        base_url=settings.airport_service_url,
        timeout=settings.airport_service_timeout_seconds,
    )


def get_event_publisher(
    session: Session = Depends(get_db_session),
) -> EventPublisher:
    # Fase 5 (ADR-026): adaptador Outbox. Usa la MISMA sesión que el repositorio y la
    # unidad de trabajo, así el itinerario y su evento entran en la misma transacción.
    # La API ya no habla con RabbitMQ: lo hace el Outbox Relay.
    return OutboxEventPublisher(session)
