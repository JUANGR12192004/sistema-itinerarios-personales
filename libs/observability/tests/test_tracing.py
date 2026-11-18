"""Pruebas de setup_tracing (ADR-035).

La fixture tracing_state captura el TracerProvider en lugar de instalarlo globalmente y
sustituye a LoggingInstrumentor (ver conftest.py).
"""

import sys
import types

import pytest
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from observability import tracing
from tests.conftest import FakeLoggingInstrumentor


class RecordingProcessor(SpanProcessor):
    """Sustituye a Batch/SimpleSpanProcessor para ver cuál elige setup_tracing y con qué exportador."""

    created: list[tuple[str, object]] = []

    def __init__(self, exporter: object, kind: str) -> None:
        RecordingProcessor.created.append((kind, exporter))

    def on_end(self, span: ReadableSpan) -> None:
        """No exporta nada: la prueba solo comprueba qué procesador se creó."""


@pytest.fixture
def recorded_processors(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, object]]:
    RecordingProcessor.created = []
    monkeypatch.setattr(tracing, "BatchSpanProcessor", lambda exporter: RecordingProcessor(exporter, "batch"))
    monkeypatch.setattr(tracing, "SimpleSpanProcessor", lambda exporter: RecordingProcessor(exporter, "simple"))
    return RecordingProcessor.created


def test_con_exportador_inyectado_los_spans_se_exportan_al_instante(tracing_state: list) -> None:
    exporter = InMemorySpanExporter()

    provider = tracing.setup_tracing("servicio-prueba", exporter=exporter)
    with provider.get_tracer("prueba").start_as_current_span("operacion"):
        pass

    assert tracing_state == [provider]
    assert [span.name for span in exporter.get_finished_spans()] == ["operacion"]
    assert provider.resource.attributes["service.name"] == "servicio-prueba"
    assert FakeLoggingInstrumentor.calls == 1


def test_en_produccion_usa_batch_con_el_exportador_otlp(
    tracing_state: list, recorded_processors: list
) -> None:
    tracing.setup_tracing("servicio-prueba")

    kind, exporter = recorded_processors[0]
    assert kind == "batch"
    assert type(exporter).__name__ == "OTLPSpanExporter"


def test_con_batch_false_usa_simple_con_el_exportador_otlp(
    tracing_state: list, recorded_processors: list
) -> None:
    """Caso de la función Lambda: puede suspenderse entre invocaciones."""
    tracing.setup_tracing("servicio-prueba", batch=False)

    kind, exporter = recorded_processors[0]
    assert kind == "simple"
    assert type(exporter).__name__ == "OTLPSpanExporter"


def test_es_idempotente(tracing_state: list) -> None:
    first = tracing.setup_tracing("uno", exporter=InMemorySpanExporter())
    second = tracing.setup_tracing("dos", exporter=InMemorySpanExporter())

    assert first is not None
    assert second is None
    assert tracing_state == [first]


@pytest.mark.parametrize("value", ["false", "FALSE"])
def test_otel_enabled_false_desactiva_las_trazas(
    tracing_state: list, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("OTEL_ENABLED", value)

    assert tracing.setup_tracing("servicio-prueba", exporter=InMemorySpanExporter()) is None
    assert tracing_state == []
    assert FakeLoggingInstrumentor.calls == 0


def test_activa_solo_los_instrumentadores_pedidos(
    tracing_state: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    activated: list[str] = []
    modules = {
        "fastapi": "FastAPIInstrumentor",
        "httpx": "HTTPXClientInstrumentor",
        "sqlalchemy": "SQLAlchemyInstrumentor",
        "pika": "PikaInstrumentor",
    }
    for name, class_name in modules.items():
        module = types.ModuleType(f"opentelemetry.instrumentation.{name}")
        instrumentor = type(class_name, (), {"instrument": lambda self, _n=name: activated.append(_n)})
        setattr(module, class_name, instrumentor)
        monkeypatch.setitem(sys.modules, module.__name__, module)

    tracing.setup_tracing(
        "servicio-prueba", exporter=InMemorySpanExporter(), instrumentors=["pika", "httpx", "desconocido"]
    )

    assert activated == ["pika", "httpx"]
