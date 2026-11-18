"""Contrato HTTP publicado de Airport Service (lado PROVEEDOR, Fase 11).

docs/openapi/airport-service.json es el "lenguaje publicado" del contexto Catálogo de Aeropuertos
(CLAUDE.md 8.1): lo que otros servicios pueden esperar de esta API. Itinerary Service lo lee en
sus pruebas (lado CONSUMIDOR) sin importar código de Airport Service.

Esta prueba falla si la API cambia y el contrato publicado no: así un cambio de rutas, códigos o
esquemas no pasa desapercibido para los consumidores. Si el cambio es intencional, regenerar el
archivo y revisar el diff en el PR:

    PowerShell:  $env:UPDATE_CONTRACTS = "1"; pytest tests/test_openapi_contract.py; Remove-Item Env:UPDATE_CONTRACTS
    CMD:         set UPDATE_CONTRACTS=1 && pytest tests/test_openapi_contract.py && set UPDATE_CONTRACTS=
    zsh:         UPDATE_CONTRACTS=1 pytest tests/test_openapi_contract.py
"""

import json
import os
from pathlib import Path

from app.main import app

CONTRACT_PATH = Path(__file__).resolve().parents[3] / "docs" / "openapi" / "airport-service.json"


def current_openapi() -> dict:
    """OpenAPI que genera FastAPI, normalizado como JSON (tuplas → listas, claves en texto)."""
    return json.loads(json.dumps(app.openapi()))


def test_el_contrato_publicado_coincide_con_la_api() -> None:
    current = current_openapi()
    if os.environ.get("UPDATE_CONTRACTS") == "1":
        CONTRACT_PATH.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(current, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        CONTRACT_PATH.write_text(content, encoding="utf-8", newline="\n")

    published = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert published == current, (
        "La API de Airport Service cambió y docs/openapi/airport-service.json no. "
        "Si el cambio es intencional, regenera el contrato (ver el docstring de esta prueba)."
    )


def test_el_contrato_documenta_lo_que_usa_itinerary_service() -> None:
    """Lo mínimo que el consumidor necesita: la ruta, su parámetro entero y el error en formato único."""
    operation = current_openapi()["paths"]["/airports/{airport_id}"]["get"]

    parameter = operation["parameters"][0]
    assert (parameter["name"], parameter["in"], parameter["schema"]["type"]) == ("airport_id", "path", "integer")
    assert {"200", "404", "503", "504"} <= set(operation["responses"])
    not_found = operation["responses"]["404"]["content"]["application/json"]["schema"]
    assert not_found == {"$ref": "#/components/schemas/ErrorResponse"}
