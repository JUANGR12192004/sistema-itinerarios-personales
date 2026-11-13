"""Configuración de logs JSON (ADR-034, Fase 9A).

Mismo patrón que los servicios Python. En Lambda el runtime pre-instala un handler
en el root logger; configure_logging agrega su propio handler al logger 'app' con
propagate=False, así los logs JSON van a stdout sin pasar por el root logger.
"""

import logging
from contextvars import ContextVar
from datetime import datetime, timezone

from pythonjsonlogger.json import JsonFormatter

_correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def set_correlation_id(value: str) -> None:
    _correlation_id_var.set(value)


def get_log_correlation_id() -> str:
    return _correlation_id_var.get()


class OTelContextFilter(logging.Filter):
    """Inyecta trace_id y span_id vacíos (se reemplaza en la Fase 9B con el contexto OTel)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = ""
        record.span_id = ""
        return True


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = _correlation_id_var.get()
        return True


class AppJsonFormatter(JsonFormatter):
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
    """Configura logs JSON en el logger 'app'. Idempotente.

    Con propagate=False los logs de 'app' van directo al StreamHandler de esta función
    y no al root logger del runtime de Lambda (evita duplicados).
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
