"""Pruebas unitarias de OutboxEventPublisher, sin PostgreSQL (ADR-026).

Se usa una sesión falsa que solo anota lo que recibe: así se comprueba que el
adaptador agrega la fila a la sesión y que NO hace commit (lo decide el caso de uso).
La prueba contra PostgreSQL real está en tests/integration/test_outbox_integration.py.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.api.dependencies import get_event_publisher
from app.application.events import ItineraryCreatedEvent
from app.domain.itinerary import Itinerary
from app.infrastructure.persistence.models import OutboxEventORM
from app.infrastructure.persistence.outbox_event_publisher import OutboxEventPublisher


def _reset_otel_global():
    import opentelemetry.trace as _trace
    from opentelemetry.util._once import Once

    _trace._TRACER_PROVIDER = None  # type: ignore[attr-defined]
    _trace._TRACER_PROVIDER_SET_ONCE = Once()  # type: ignore[attr-defined]


@pytest.fixture
def reset_tracing():
    import observability.tracing as tracing_module

    tracing_module._initialized = False
    _reset_otel_global()
    yield
    tracing_module._initialized = False
    _reset_otel_global()


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
    assert row.failed_at is None


def test_no_hace_commit():
    """El commit lo hace el caso de uso con UnitOfWork, junto con el itinerario."""
    session = FakeSession()

    OutboxEventPublisher(session).publish(_event())  # type: ignore[arg-type]

    assert session.commits == 0


def test_la_api_inyecta_el_adaptador_outbox():
    """dependencies.py entrega OutboxEventPublisher sobre la sesión de la solicitud."""
    publisher = get_event_publisher(session=FakeSession())  # type: ignore[arg-type]

    assert isinstance(publisher, OutboxEventPublisher)


def test_traceparent_es_none_sin_span_activo():
    """Sin OTel configurado, propagate.inject devuelve un carrier vacío → traceparent None."""
    session = FakeSession()

    OutboxEventPublisher(session).publish(_event())  # type: ignore[arg-type]

    row = session.added[0]
    assert row.traceparent is None


def test_traceparent_captura_el_span_activo(reset_tracing):
    """Con un span OTel activo, OutboxEventPublisher captura su traceparent W3C (ADR-037)."""
    from opentelemetry import trace
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from observability.tracing import setup_tracing

    setup_tracing("itinerary-service-test", exporter=InMemorySpanExporter())
    session = FakeSession()

    with trace.get_tracer("test").start_as_current_span("crear-itinerario") as span:
        OutboxEventPublisher(session).publish(_event())  # type: ignore[arg-type]
        ctx = span.get_span_context()

    row = session.added[0]
    assert row.traceparent is not None
    # El traceparent W3C tiene la forma 00-{trace_id_32hex}-{span_id_16hex}-{flags_2hex}
    assert row.traceparent.startswith("00-")
    expected_trace_id = format(ctx.trace_id, "032x")
    assert expected_trace_id in row.traceparent
