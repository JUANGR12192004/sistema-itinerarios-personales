"""Configuración de OpenTelemetry para SendNotificationFunction (ADR-035, Fase 9B).

La función se ejecuta en Lambda (RIE en local). Usa SimpleSpanProcessor para que
los spans se exporten de inmediato antes de que el contenedor se suspenda
entre invocaciones; BatchSpanProcessor podría perder spans.
"""

import logging
import os

from opentelemetry import trace
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter

logger = logging.getLogger(__name__)

_initialized = False


def setup_tracing(service_name: str, exporter: SpanExporter | None = None) -> TracerProvider | None:
    """Configura el TracerProvider global e instrumenta SQLAlchemy. Idempotente."""
    global _initialized
    if _initialized:
        return None
    _initialized = True

    if os.environ.get("OTEL_ENABLED", "true").lower() == "false":
        logger.debug("OTEL_ENABLED=false: trazas desactivadas")
        return None

    if exporter is None:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter()

    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    SQLAlchemyInstrumentor().instrument()
    LoggingInstrumentor().instrument()

    logger.info("OpenTelemetry configurado para '%s'", service_name)
    return provider
