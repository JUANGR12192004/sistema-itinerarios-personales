"""Configuración de OpenTelemetry para Airport Service (ADR-035, Fase 9B).

Llama a `setup_tracing` una vez al arrancar el servicio. Idempotente.
En las pruebas se inyecta un `InMemorySpanExporter` para verificar los spans.
La variable `OTEL_ENABLED=false` desactiva completamente el envío de trazas
(útil en entornos sin Jaeger).
"""

import logging
import os

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, SpanExporter

logger = logging.getLogger(__name__)

_initialized = False


def setup_tracing(service_name: str, exporter: SpanExporter | None = None) -> TracerProvider | None:
    """Configura el TracerProvider global e instrumenta FastAPI y httpx.

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

    # Cuando se inyecta un exporter (modo test), se usa SimpleSpanProcessor para que
    # los spans se exporten de inmediato y puedan inspeccionarse en la prueba.
    # En producción (exporter=None) se crea OTLPSpanExporter y se usa BatchSpanProcessor
    # para no bloquear el hilo de la solicitud HTTP.
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
    LoggingInstrumentor().instrument()

    logger.info("OpenTelemetry configurado para '%s'", service_name)
    return provider
