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
    """Sesión SQLAlchemy por solicitud: rollback si hay excepción y cierre al terminar.

    NO confirma (commit) la transacción: lo hace cada caso de uso de escritura con el
    puerto UnitOfWork. En FastAPI 0.162 el código que va después del `yield` corre
    DESPUÉS de enviar la respuesta; un commit aquí haría que el cliente recibiera el
    200/204 antes de que los cambios estuvieran guardados (ADR-019). Si un caso de uso
    olvida el commit, sus cambios se descartan al cerrar la sesión.
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
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
