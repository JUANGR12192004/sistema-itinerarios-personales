"""Contrato HTTP con Airport Service (lado CONSUMIDOR, Fase 11).

Lee el contrato que publica Airport Service (docs/openapi/airport-service.json, verificado contra
la API real por las pruebas de Airport) sin importar su código: los servicios solo se conocen por
su API (CLAUDE.md 7.2).

Comprueba que HttpAirportCatalogAdapter llama a la ruta documentada y que CADA respuesta
documentada de GET /airports/{airport_id} tiene un comportamiento decidido. Si Airport Service
agrega un código nuevo, esta prueba falla hasta que se decida cómo tratarlo aquí.
"""

import json
from pathlib import Path

import httpx
import pytest
import respx

from app.application.exceptions import (
    AirportNotFoundInCatalogError,
    AirportServiceTimeoutError,
    AirportServiceUnavailableError,
)
from app.infrastructure.airport_client.http_airport_catalog_adapter import HttpAirportCatalogAdapter

CONTRACT_PATH = Path(__file__).resolve().parents[4] / "docs" / "openapi" / "airport-service.json"
BASE_URL = "http://airport-service:8001"
OPERATION_PATH = "/airports/{airport_id}"

# Respuesta documentada → qué hace Itinerary Service (None = el aeropuerto existe)
EXPECTED_BEHAVIOR: dict[str, type[Exception] | None] = {
    "200": None,
    "404": AirportNotFoundInCatalogError,  # → 422 AIRPORT_NOT_FOUND al crear el itinerario
    "422": AirportServiceUnavailableError,  # id inválido: no ocurre (el dominio exige id >= 1)
    "502": AirportServiceUnavailableError,  # → 503
    "503": AirportServiceUnavailableError,  # → 503
    "504": AirportServiceTimeoutError,  # → 504
}


def documented_responses() -> dict:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    return contract["paths"][OPERATION_PATH]["get"]["responses"]


def test_cada_respuesta_documentada_tiene_un_comportamiento_decidido() -> None:
    assert set(documented_responses()) == set(EXPECTED_BEHAVIOR)


@pytest.mark.parametrize(("status", "expected"), EXPECTED_BEHAVIOR.items())
@respx.mock
def test_el_adaptador_trata_cada_respuesta_documentada(status: str, expected: type[Exception] | None) -> None:
    route = respx.get(f"{BASE_URL}/airports/7").mock(return_value=httpx.Response(int(status), json={}))
    adapter = HttpAirportCatalogAdapter(base_url=BASE_URL, timeout=1.0)

    if expected is None:
        adapter.verify_exists(7)
    else:
        with pytest.raises(expected):
            adapter.verify_exists(7)

    assert route.called
