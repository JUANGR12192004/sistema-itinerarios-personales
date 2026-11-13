"""Pruebas de la configuración de OpenTelemetry (ADR-035, Fase 9B)."""

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

import app.tracing as tracing_module
from app.tracing import setup_tracing


def _reset_otel_global():
    import opentelemetry.trace as _trace
    from opentelemetry.util._once import Once

    _trace._TRACER_PROVIDER = None  # type: ignore[attr-defined]
    _trace._TRACER_PROVIDER_SET_ONCE = Once()  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def reset_tracing():
    original_initialized = tracing_module._initialized
    tracing_module._initialized = False
    _reset_otel_global()
    yield
    tracing_module._initialized = original_initialized
    _reset_otel_global()


def test_setup_tracing_creates_tracer_provider():
    exporter = InMemorySpanExporter()
    provider = setup_tracing("itinerary-service-test", exporter=exporter)

    assert isinstance(provider, TracerProvider)


def test_setup_tracing_records_spans():
    exporter = InMemorySpanExporter()
    setup_tracing("itinerary-service-test", exporter=exporter)

    from opentelemetry import trace

    with trace.get_tracer("test").start_as_current_span("span-prueba"):
        pass

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "span-prueba"


def test_setup_tracing_is_idempotent():
    exporter1 = InMemorySpanExporter()
    exporter2 = InMemorySpanExporter()

    setup_tracing("itinerary-service-test", exporter=exporter1)
    result = setup_tracing("itinerary-service-test", exporter=exporter2)

    assert result is None

    from opentelemetry import trace

    with trace.get_tracer("test").start_as_current_span("span-idempotencia"):
        pass

    assert len(exporter1.get_finished_spans()) == 1
    assert len(exporter2.get_finished_spans()) == 0


def test_setup_tracing_disabled_when_otel_enabled_false(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "false")
    result = setup_tracing("itinerary-service-test", exporter=InMemorySpanExporter())

    assert result is None


def test_otel_context_filter_reads_active_span():
    """OTelContextFilter lee trace_id y span_id del span activo (ADR-035)."""
    import json
    import logging
    from io import StringIO

    from app.logging_config import AppJsonFormatter, CorrelationIdFilter, OTelContextFilter

    exporter = InMemorySpanExporter()
    setup_tracing("itinerary-service-test", exporter=exporter)

    from opentelemetry import trace

    stream = StringIO()
    test_logger = logging.getLogger("app.it.tracing.test")
    test_logger.propagate = False
    test_logger.handlers.clear()
    handler = logging.StreamHandler(stream)
    handler.addFilter(OTelContextFilter())
    handler.addFilter(CorrelationIdFilter())
    handler.setFormatter(AppJsonFormatter("itinerary-service-test"))
    test_logger.addHandler(handler)
    test_logger.setLevel(logging.DEBUG)

    tracer = trace.get_tracer("test")
    with tracer.start_as_current_span("span-it") as span:
        test_logger.info("dentro del span")
        ctx = span.get_span_context()
        expected_trace_id = format(ctx.trace_id, "032x")
        expected_span_id = format(ctx.span_id, "016x")

    data = json.loads(stream.getvalue())
    assert data["trace_id"] == expected_trace_id
    assert data["span_id"] == expected_span_id
    assert data["trace_id"] != ""
    assert data["span_id"] != ""
