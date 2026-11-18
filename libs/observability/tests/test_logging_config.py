"""Pruebas de los logs JSON compartidos (ADR-034)."""

import json
import logging

import pytest
from opentelemetry.sdk.trace import TracerProvider

from observability.logging_config import (
    AppJsonFormatter,
    CorrelationIdFilter,
    OTelContextFilter,
    configure_logging,
    get_log_correlation_id,
    set_correlation_id,
)

FIELDS = ["timestamp", "level", "service", "logger", "message", "correlation_id", "trace_id", "span_id"]


def make_record(message: str = "hola", **extra: object) -> logging.LogRecord:
    record = logging.LogRecord("app.prueba", logging.INFO, __file__, 1, message, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def format_record(record: logging.LogRecord) -> dict:
    return json.loads(AppJsonFormatter("servicio-prueba").format(record))


def test_el_formato_tiene_los_campos_de_adr_034_en_orden_y_luego_los_extra() -> None:
    data = format_record(make_record(correlation_id="c-1", itinerary_id="it-9"))

    assert list(data)[: len(FIELDS)] == FIELDS
    assert data["service"] == "servicio-prueba"
    assert data["level"] == "INFO"
    assert data["message"] == "hola"
    assert data["correlation_id"] == "c-1"
    assert data["itinerary_id"] == "it-9"
    assert data["timestamp"].endswith("Z")


def test_sin_filtros_los_campos_de_contexto_quedan_vacios() -> None:
    data = format_record(make_record())

    assert (data["correlation_id"], data["trace_id"], data["span_id"]) == ("", "", "")


def test_set_y_get_correlation_id_usan_el_contexto_actual() -> None:
    set_correlation_id("abc-123")

    assert get_log_correlation_id() == "abc-123"
    set_correlation_id("")


def test_el_filtro_de_correlation_id_no_reemplaza_un_valor_explicito() -> None:
    set_correlation_id("del-contexto")
    explicit = make_record(correlation_id="del-mensaje")
    implicit = make_record()

    CorrelationIdFilter().filter(explicit)
    CorrelationIdFilter().filter(implicit)

    assert explicit.correlation_id == "del-mensaje"
    assert implicit.correlation_id == "del-contexto"
    set_correlation_id("")


def test_el_filtro_otel_copia_trace_id_y_span_id_del_span_activo() -> None:
    tracer = TracerProvider().get_tracer("prueba")
    record = make_record()

    with tracer.start_as_current_span("operacion") as span:
        OTelContextFilter().filter(record)
        context = span.get_span_context()

    assert record.trace_id == format(context.trace_id, "032x")
    assert record.span_id == format(context.span_id, "016x")
    assert len(record.trace_id) == 32 and len(record.span_id) == 16


def test_configure_logging_escribe_json_en_el_logger_app(
    app_logger: logging.Logger, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging("debug", "servicio-prueba")

    logging.getLogger("app.modulo").debug("mensaje de prueba")

    line = json.loads(capsys.readouterr().err.strip())
    assert line["message"] == "mensaje de prueba"
    assert line["logger"] == "app.modulo"
    assert app_logger.level == logging.DEBUG
    assert app_logger.propagate is False


def test_configure_logging_es_idempotente(app_logger: logging.Logger) -> None:
    configure_logging("INFO", "uno")
    configure_logging("DEBUG", "dos")

    assert len(app_logger.handlers) == 1
    assert app_logger.level == logging.INFO
