"""Pruebas del manejador de errores inesperados (500) de Airport Service.

Los manejadores de errores son funciones normales (`def`): Starlette las ejecuta en
un hilo del threadpool. Estas pruebas comprueban que la respuesta no cambia y que los
logs conservan lo que se necesita para diagnosticar: la traza de la excepción
(traceback) en el 500 y el correlation ID en los errores conocidos.
"""

import logging
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.correlation import CORRELATION_ID_HEADER
from app.api.dependencies import get_airport_provider
from app.application.exceptions import AirportProviderUnavailableError
from app.main import create_app
from observability.logging_config import CorrelationIdFilter
from tests.fakes import FakeAirportProvider

ERRORS_LOGGER = "app.api.errors"


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
    logger = logging.getLogger(ERRORS_LOGGER)
    logger.addHandler(handler)
    yield handler
    logger.removeHandler(handler)


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_airport_provider] = lambda: FakeAirportProvider(
        error=RuntimeError("fallo inesperado de prueba")
    )
    # raise_server_exceptions=False: se quiere ver la respuesta 500, no la excepción en la prueba
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def test_unexpected_error_returns_500_in_the_common_format(client: TestClient) -> None:
    response = client.get("/airports", headers={CORRELATION_ID_HEADER: "prueba-500"})

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "Ocurrió un error interno inesperado",
            "details": {},
        },
        "correlation_id": "prueba-500",
    }


def test_unexpected_error_log_keeps_the_traceback(client: TestClient, log_handler: ListHandler) -> None:
    # En un hilo del threadpool no hay "excepción en curso" (sys.exc_info() está vacío):
    # el manejador pasa la excepción explícitamente para que el traceback llegue al log.
    client.get("/airports")

    [record] = [r for r in log_handler.records if r.levelno == logging.ERROR]
    assert record.getMessage() == "Error inesperado procesando GET /airports"
    assert record.exc_info is not None
    assert record.exc_info[0] is RuntimeError


def test_known_error_handlers_keep_the_correlation_id_in_their_logs(log_handler: ListHandler) -> None:
    app = create_app()
    app.dependency_overrides[get_airport_provider] = lambda: FakeAirportProvider(
        error=AirportProviderUnavailableError("API Colombia caída (prueba)")
    )
    response = TestClient(app).get("/airports", headers={CORRELATION_ID_HEADER: "prueba-503"})

    assert response.status_code == 503
    [record] = [r for r in log_handler.records if r.levelno == logging.WARNING]
    assert record.correlation_id == "prueba-503"  # type: ignore[attr-defined]
