"""Configuración de OpenTelemetry para Itinerary Service (ADR-035, Fase 9B).

Instrumenta FastAPI, httpx (llamadas a Airport Service), SQLAlchemy y pika.
"""

import logging
import os

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.pika import PikaInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, SpanExporter

logger = logging.getLogger(__name__)

_initialized = False


def setup_tracing(service_name: str, exporter: SpanExporter | None = None) -> TracerProvider | None:
    """Configura el TracerProvider global e instrumenta FastAPI, httpx, SQLAlchemy y pika.

    Idempotente: solo configura en la primera llamada.
    Devuelve el provider creado, o None si ya estaba inicializado o OTEL está desactivado.
    """
    global _initialized
    if _initialized:
        return None
    _initialized = True

    if os.environ.get("OTEL_ENABLED", "true").lower() == "false":
        logger.debug("OTEL_ENABLED=false: trazas desactivadas")
        return None

    if exporter is not None:
        processor = SimpleSpanProcessor(exporter)
    else:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        processor = BatchSpanProcessor(OTLPSpanExporter())

    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()
    PikaInstrumentor().instrument()
    LoggingInstrumentor().instrument()

    logger.info("OpenTelemetry configurado para '%s'", service_name)
    return provider
