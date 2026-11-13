"""Configuración de logs JSON (ADR-034, Fase 9A).

Todos los servicios del proyecto usan la misma estructura:
- OTelContextFilter: inyecta trace_id y span_id. Vacíos en la Fase 9A;
  en la 9B se reemplaza por el contexto activo de OpenTelemetry.
- CorrelationIdFilter: lee el correlation_id del ContextVar que establece el middleware HTTP.
- AppJsonFormatter: formato JSON con los 8 campos acordados en ADR-034.
- configure_logging: idempotente, configura solo el logger 'app'.
"""

import logging
from contextvars import ContextVar
from datetime import datetime, timezone

from pythonjsonlogger.json import JsonFormatter

# ContextVar por solicitud (asyncio copia el contexto por tarea, así que cada
# solicitud HTTP tiene su propio valor). El relay y el trigger lo dejan vacío en 9A.
_correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def set_correlation_id(value: str) -> None:
    """Establece el correlation ID del contexto actual (llamado por el middleware HTTP)."""
    _correlation_id_var.set(value)


def get_log_correlation_id() -> str:
    """Devuelve el correlation ID activo (vacío si no hay solicitud en curso)."""
    return _correlation_id_var.get()


class OTelContextFilter(logging.Filter):
    """Inyecta trace_id y span_id del span activo de OpenTelemetry (ADR-035, Fase 9B).

    Si no hay span activo (o OTEL está desactivado), deja los campos vacíos.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        from opentelemetry import trace

        ctx = trace.get_current_span().get_span_context()
        record.trace_id = format(ctx.trace_id, "032x") if ctx.is_valid else ""
        record.span_id = format(ctx.span_id, "016x") if ctx.is_valid else ""
        return True


class CorrelationIdFilter(logging.Filter):
    """Inyecta el correlation_id del contexto actual si el llamador no lo pasa en extra."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = _correlation_id_var.get()
        return True


class AppJsonFormatter(JsonFormatter):
    """Formato JSON con los campos de ADR-034.

    Campos en orden: timestamp, level, service, logger, message,
    correlation_id, trace_id, span_id. Se incluyen además los campos
    extra que el llamador pase vía extra={...}.
    """

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self._service_name = service_name

    def add_fields(
        self,
        log_data: dict,
        record: logging.LogRecord,
        message_dict: dict,
    ) -> None:
        super().add_fields(log_data, record, message_dict)
        ordered: dict = {
            "timestamp": (
                datetime.fromtimestamp(record.created, tz=timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z")
            ),
            "level": record.levelname,
            "service": self._service_name,
            "logger": record.name,
            "message": log_data.get("message", record.getMessage()),
            "correlation_id": getattr(record, "correlation_id", ""),
            "trace_id": getattr(record, "trace_id", ""),
            "span_id": getattr(record, "span_id", ""),
        }
        for key, value in log_data.items():
            if key not in ordered:
                ordered[key] = value
        log_data.clear()
        log_data.update(ordered)


def configure_logging(level: str, service_name: str) -> None:
    """Configura logs JSON en el logger 'app'. Idempotente: no reinicializa si ya hay handler.

    Se llama una vez al arrancar el servicio (o al primer acceso del handler de Lambda).
    """
    app_logger = logging.getLogger("app")
    if app_logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.addFilter(OTelContextFilter())
    handler.addFilter(CorrelationIdFilter())
    handler.setFormatter(AppJsonFormatter(service_name))
    app_logger.setLevel(level.upper())
    app_logger.addHandler(handler)
    app_logger.propagate = False
