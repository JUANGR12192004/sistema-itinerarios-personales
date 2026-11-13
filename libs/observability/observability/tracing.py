"""Configuración de OpenTelemetry compartida por todos los componentes (ADR-035, Fase 9B).

Llama a `setup_tracing` una vez al arrancar. Idempotente.
En las pruebas se inyecta un `InMemorySpanExporter` para verificar los spans sin Jaeger.
La variable `OTEL_ENABLED=false` desactiva completamente el envío de trazas.

Parámetros de `setup_tracing`:
  service_name  nombre del servicio (aparece en Jaeger y en el campo 'service' de los logs)
  exporter      SpanExporter inyectado en pruebas; None en producción
  instrumentors lista de bibliotecas a instrumentar: "fastapi", "httpx", "sqlalchemy", "pika"
  batch         True  → BatchSpanProcessor (producción, servicios de larga vida)
                False → SimpleSpanProcessor siempre (Lambda: puede suspenderse entre invocaciones)

LoggingInstrumentor siempre se activa (todos los componentes usan logs).
"""

import logging
import os

from opentelemetry import trace
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, SpanExporter

logger = logging.getLogger(__name__)

_initialized = False


def setup_tracing(
    service_name: str,
    exporter: SpanExporter | None = None,
    instrumentors: list[str] | None = None,
    batch: bool = True,
) -> TracerProvider | None:
    """Configura el TracerProvider global e instrumenta las bibliotecas solicitadas.

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

    # Modo prueba: SimpleSpanProcessor para que los spans se exporten de inmediato.
    # Producción con batch=True: BatchSpanProcessor no bloquea el hilo de la solicitud.
    # Producción con batch=False (Lambda): SimpleSpanProcessor exporta antes de que el
    # contenedor se suspenda entre invocaciones; BatchSpanProcessor podría perder spans.
    if exporter is not None:
        processor = SimpleSpanProcessor(exporter)
    elif batch:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        processor = BatchSpanProcessor(OTLPSpanExporter())
    else:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        processor = SimpleSpanProcessor(OTLPSpanExporter())

    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    _apply_instrumentors(instrumentors or [])
    LoggingInstrumentor().instrument()

    logger.info("OpenTelemetry configurado para '%s'", service_name)
    return provider


def _apply_instrumentors(names: list[str]) -> None:
    """Activa los instrumentadores solicitados con importación diferida."""
    for name in names:
        if name == "fastapi":
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor().instrument()
        elif name == "httpx":
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

            HTTPXClientInstrumentor().instrument()
        elif name == "sqlalchemy":
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

            SQLAlchemyInstrumentor().instrument()
        elif name == "pika":
            from opentelemetry.instrumentation.pika import PikaInstrumentor

            PikaInstrumentor().instrument()
