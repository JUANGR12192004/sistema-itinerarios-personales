"""Pruebas de la configuración de logs JSON (ADR-034, Fase 9A)."""

import json
import logging
from io import StringIO

from app.logging_config import (
    AppJsonFormatter,
    CorrelationIdFilter,
    OTelContextFilter,
    configure_logging,
    set_correlation_id,
)

REQUIRED_FIELDS = {"timestamp", "level", "service", "logger", "message", "correlation_id", "trace_id", "span_id"}


def _make_logger(name: str, service: str) -> tuple[logging.Logger, StringIO]:
    """Crea un logger aislado con el formatter JSON y devuelve el stream de captura."""
    stream = StringIO()
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.handlers.clear()
    handler = logging.StreamHandler(stream)
    handler.addFilter(OTelContextFilter())
    handler.addFilter(CorrelationIdFilter())
    handler.setFormatter(AppJsonFormatter(service))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger, stream


def test_formatter_produces_all_required_fields():
    logger, stream = _make_logger("app.test.fields", "airport-service")

    logger.info("prueba de campos")

    data = json.loads(stream.getvalue())
    assert REQUIRED_FIELDS.issubset(data.keys())


def test_formatter_values_are_correct():
    logger, stream = _make_logger("app.test.values", "airport-service")

    logger.warning("mensaje de advertencia")

    data = json.loads(stream.getvalue())
    assert data["level"] == "WARNING"
    assert data["service"] == "airport-service"
    assert data["logger"] == "app.test.values"
    assert data["message"] == "mensaje de advertencia"
    assert data["trace_id"] == ""
    assert data["span_id"] == ""
    assert data["timestamp"].endswith("Z")


def test_formatter_timestamp_is_iso8601_utc():
    logger, stream = _make_logger("app.test.ts", "airport-service")

    logger.info("ts")

    data = json.loads(stream.getvalue())
    ts = data["timestamp"]
    # Debe terminar en Z (UTC) y tener el formato básico de ISO 8601
    assert ts.endswith("Z")
    assert "T" in ts


def test_correlation_id_filter_reads_context_var():
    set_correlation_id("cid-airport-test-99")
    logger, stream = _make_logger("app.test.cid", "airport-service")

    logger.info("con cid")

    data = json.loads(stream.getvalue())
    assert data["correlation_id"] == "cid-airport-test-99"


def test_otel_filter_adds_empty_trace_and_span():
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="x",
        args=(),
        exc_info=None,
    )
    OTelContextFilter().filter(record)

    assert record.trace_id == ""
    assert record.span_id == ""


def test_configure_logging_is_idempotent():
    app_logger = logging.getLogger("app")
    original_handlers = app_logger.handlers[:]
    app_logger.handlers.clear()

    try:
        configure_logging("INFO", "airport-service")
        count_after_first = len(app_logger.handlers)
        configure_logging("INFO", "airport-service")
        count_after_second = len(app_logger.handlers)

        assert count_after_first == 1
        assert count_after_second == 1
    finally:
        app_logger.handlers.clear()
        app_logger.handlers.extend(original_handlers)


def test_extra_fields_are_included():
    logger, stream = _make_logger("app.test.extra", "airport-service")

    logger.info("con extra", extra={"airport_id": 5, "cache": "HIT"})

    data = json.loads(stream.getvalue())
    assert data["airport_id"] == 5
    assert data["cache"] == "HIT"
