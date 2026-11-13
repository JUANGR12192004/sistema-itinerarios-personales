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
    logger, stream = _make_logger("app.it.fields", "itinerary-service")

    logger.info("prueba de campos")

    data = json.loads(stream.getvalue())
    assert REQUIRED_FIELDS.issubset(data.keys())


def test_formatter_values_are_correct():
    logger, stream = _make_logger("app.it.values", "itinerary-service")

    logger.error("error de prueba")

    data = json.loads(stream.getvalue())
    assert data["level"] == "ERROR"
    assert data["service"] == "itinerary-service"
    assert data["logger"] == "app.it.values"
    assert data["message"] == "error de prueba"
    assert data["trace_id"] == ""
    assert data["span_id"] == ""


def test_correlation_id_filter_reads_context_var():
    set_correlation_id("cid-it-test-77")
    logger, stream = _make_logger("app.it.cid", "itinerary-service")

    logger.info("con cid")

    data = json.loads(stream.getvalue())
    assert data["correlation_id"] == "cid-it-test-77"


def test_configure_logging_is_idempotent():
    app_logger = logging.getLogger("app")
    original_handlers = app_logger.handlers[:]
    app_logger.handlers.clear()

    try:
        configure_logging("INFO", "itinerary-service")
        count_after_first = len(app_logger.handlers)
        configure_logging("INFO", "itinerary-service")
        count_after_second = len(app_logger.handlers)

        assert count_after_first == 1
        assert count_after_second == 1
    finally:
        app_logger.handlers.clear()
        app_logger.handlers.extend(original_handlers)
