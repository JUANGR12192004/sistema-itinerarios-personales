"""El log de un error 500 lleva el mismo correlation ID que la respuesta.

El 500 lo atiende ServerErrorMiddleware, la capa más externa de la aplicación. Allí no
se ve el ContextVar que fija el middleware de correlation ID (corre dentro de
metrics_middleware, en otra tarea), así que el manejador debe pasar el valor al log.
"""

import logging
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_itinerary_repository
from app.main import app
from observability.logging_config import CorrelationIdFilter
from tests.fakes import FakeItineraryRepository

ERROR_HANDLER_LOGGER = "app.api.error_handler"


class BrokenRepository(FakeItineraryRepository):
    def list_all(self) -> list:
        raise RuntimeError("Error simulado")


class ListHandler(logging.Handler):
    """Guarda los registros de log, con el filtro de correlation ID de los logs JSON."""

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []
        self.addFilter(CorrelationIdFilter())

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def log_handler() -> Iterator[ListHandler]:
    handler = ListHandler()
    logger = logging.getLogger(ERROR_HANDLER_LOGGER)
    logger.addHandler(handler)
    yield handler
    logger.removeHandler(handler)


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_itinerary_repository] = lambda: BrokenRepository()
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _error_record(handler: ListHandler) -> logging.LogRecord:
    [record] = [r for r in handler.records if r.levelno == logging.ERROR]
    return record


def test_log_del_500_tiene_el_correlation_id_recibido(client: TestClient, log_handler: ListHandler):
    response = client.get("/itineraries", headers={"X-Correlation-ID": "prueba-500"})

    assert response.status_code == 500
    assert response.json()["correlation_id"] == "prueba-500"
    record = _error_record(log_handler)
    assert record.correlation_id == "prueba-500"
    assert record.exc_info is not None


def test_log_y_respuesta_del_500_comparten_el_correlation_id_generado(
    client: TestClient, log_handler: ListHandler
):
    response = client.get("/itineraries")

    record = _error_record(log_handler)
    assert record.correlation_id
    assert record.correlation_id == response.json()["correlation_id"]
    assert record.correlation_id == response.headers["X-Correlation-ID"]


@pytest.mark.parametrize(
    "headers",
    [{}, {"X-Correlation-ID": "x" * 200}],
    ids=["sin-header", "header-de-200-caracteres"],
)
def test_cuerpo_y_header_de_un_error_conocido_coinciden(headers: dict):
    # Error manejado (422): el cuerpo debe traer el mismo correlation ID que el header que
    # devuelve el middleware (generado, o recortado a 128 caracteres).
    response = TestClient(app).get("/itineraries/no-es-uuid", headers=headers)

    assert response.status_code == 422
    assert response.json()["correlation_id"] == response.headers["X-Correlation-ID"]
    assert len(response.json()["correlation_id"]) <= 128
