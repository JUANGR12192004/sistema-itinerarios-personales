"""Pruebas unitarias de OutboxEventPublisher, sin PostgreSQL (ADR-026).

Se usa una sesión falsa que solo anota lo que recibe: así se comprueba que el
adaptador agrega la fila a la sesión y que NO hace commit (lo decide el caso de uso).
La prueba contra PostgreSQL real está en tests/integration/test_outbox_integration.py.
"""

from datetime import datetime, timedelta, timezone

from app.api.dependencies import get_event_publisher
from app.application.events import ItineraryCreatedEvent
from app.domain.itinerary import Itinerary
from app.infrastructure.persistence.models import OutboxEventORM
from app.infrastructure.persistence.outbox_event_publisher import OutboxEventPublisher


class FakeSession:
    """Sesión mínima: guarda los objetos agregados y cuenta los commits."""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.commits = 0

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def commit(self) -> None:
        self.commits += 1


def _event() -> ItineraryCreatedEvent:
    itinerary = Itinerary.create(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=datetime.now(timezone.utc) + timedelta(days=30),
        duration_minutes=75,
    )
    return ItineraryCreatedEvent.from_itinerary(itinerary, "cid-1")


def test_agrega_una_fila_de_outbox_a_la_sesion():
    session = FakeSession()
    event = _event()

    OutboxEventPublisher(session).publish(event)  # type: ignore[arg-type]

    assert len(session.added) == 1
    row = session.added[0]
    assert isinstance(row, OutboxEventORM)
    assert row.id == event.event_id
    assert row.aggregate_type == "itinerary"
    assert row.aggregate_id == event.itinerary_id
    assert row.event_type == "itinerary.created"
    assert row.event_version == 1
    assert row.payload == event.to_dict()
    assert row.occurred_at == event.occurred_at


def test_la_fila_queda_pendiente():
    session = FakeSession()

    OutboxEventPublisher(session).publish(_event())  # type: ignore[arg-type]

    row = session.added[0]
    assert row.published_at is None
    assert row.attempts == 0
    assert row.last_error is None


def test_no_hace_commit():
    """El commit lo hace el caso de uso con UnitOfWork, junto con el itinerario."""
    session = FakeSession()

    OutboxEventPublisher(session).publish(_event())  # type: ignore[arg-type]

    assert session.commits == 0


def test_la_api_inyecta_el_adaptador_outbox():
    """dependencies.py entrega OutboxEventPublisher sobre la sesión de la solicitud."""
    publisher = get_event_publisher(session=FakeSession())  # type: ignore[arg-type]

    assert isinstance(publisher, OutboxEventPublisher)
