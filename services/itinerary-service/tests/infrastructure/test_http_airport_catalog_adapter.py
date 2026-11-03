"""Pruebas del HttpAirportCatalogAdapter con respx (sin llamadas reales a Airport Service)."""

import httpx
import pytest
import respx

from app.application.exceptions import (
    AirportNotFoundInCatalogError,
    AirportServiceTimeoutError,
    AirportServiceUnavailableError,
)
from app.infrastructure.airport_client.http_airport_catalog_adapter import (
    HttpAirportCatalogAdapter,
)

BASE_URL = "http://airport-service"
TIMEOUT = 5.0


def _adapter() -> HttpAirportCatalogAdapter:
    return HttpAirportCatalogAdapter(base_url=BASE_URL, timeout=TIMEOUT)


@respx.mock
def test_aeropuerto_existe_no_lanza():
    """200 de Airport Service → verify_exists retorna sin lanzar ninguna excepción."""
    respx.get(f"{BASE_URL}/airports/1").mock(
        return_value=httpx.Response(200, json={"id": 1, "name": "El Dorado"})
    )
    _adapter().verify_exists(1)


@respx.mock
def test_aeropuerto_no_encontrado_lanza_error_con_id():
    """404 de Airport Service → AirportNotFoundInCatalogError con el id del aeropuerto."""
    respx.get(f"{BASE_URL}/airports/999").mock(return_value=httpx.Response(404))
    adapter = _adapter()
    with pytest.raises(AirportNotFoundInCatalogError) as exc_info:
        adapter.verify_exists(999)
    assert exc_info.value.airport_id == 999


@respx.mock
def test_servicio_no_disponible_503():
    """503 de Airport Service → AirportServiceUnavailableError (no es timeout)."""
    respx.get(f"{BASE_URL}/airports/1").mock(return_value=httpx.Response(503))
    adapter = _adapter()
    with pytest.raises(AirportServiceUnavailableError) as exc_info:
        adapter.verify_exists(1)
    assert not isinstance(exc_info.value, AirportServiceTimeoutError)


@respx.mock
def test_timeout_reportado_por_airport_service_504():
    """504 de Airport Service → AirportServiceTimeoutError."""
    respx.get(f"{BASE_URL}/airports/1").mock(return_value=httpx.Response(504))
    adapter = _adapter()
    with pytest.raises(AirportServiceTimeoutError):
        adapter.verify_exists(1)


@respx.mock
def test_timeout_de_red():
    """httpx.TimeoutException (timeout de red) → AirportServiceTimeoutError."""
    respx.get(f"{BASE_URL}/airports/1").mock(
        side_effect=httpx.TimeoutException("network timeout")
    )
    adapter = _adapter()
    with pytest.raises(AirportServiceTimeoutError):
        adapter.verify_exists(1)


@respx.mock
def test_error_de_conexion():
    """httpx.ConnectError (red inaccesible) → AirportServiceUnavailableError (no timeout)."""
    respx.get(f"{BASE_URL}/airports/1").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    adapter = _adapter()
    with pytest.raises(AirportServiceUnavailableError) as exc_info:
        adapter.verify_exists(1)
    assert not isinstance(exc_info.value, AirportServiceTimeoutError)


@respx.mock
def test_respuesta_inesperada_502():
    """Código inesperado (502) → AirportServiceUnavailableError (no timeout)."""
    respx.get(f"{BASE_URL}/airports/1").mock(return_value=httpx.Response(502))
    adapter = _adapter()
    with pytest.raises(AirportServiceUnavailableError) as exc_info:
        adapter.verify_exists(1)
    assert not isinstance(exc_info.value, AirportServiceTimeoutError)
