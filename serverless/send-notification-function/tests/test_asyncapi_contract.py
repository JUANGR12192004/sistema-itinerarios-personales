"""Contrato de ItineraryCreatedEvent v1 (lado CONSUMIDOR, Fase 11).

docs/asyncapi/asyncapi.yaml describe el evento que publica Itinerary Service; sus pruebas
comprueban el lado PRODUCTOR. Aquí se comprueba que la función acepta lo que el contrato promete
y nunca exige más (Tolerant Reader): si la función empezara a requerir un campo que el contrato
no garantiza, rechazaría eventos válidos y los mandaría a la DLQ.
"""

from pathlib import Path

import pytest
import yaml

from app.application.exceptions import InvalidEventError
from app.event_schema import ItineraryCreatedDataSchema, ItineraryCreatedEventSchema, parse_event

ASYNCAPI_PATH = Path(__file__).resolve().parents[3] / "docs" / "asyncapi" / "asyncapi.yaml"


def load_asyncapi() -> dict:
    with ASYNCAPI_PATH.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


ASYNCAPI = load_asyncapi()
MESSAGE = ASYNCAPI["components"]["messages"]["ItineraryCreatedEvent"]
SCHEMAS = ASYNCAPI["components"]["schemas"]
EXAMPLES = [example["payload"] for example in MESSAGE["examples"]]


def required_by_function(model: type) -> set[str]:
    return {name for name, field in model.model_fields.items() if field.is_required()}


@pytest.mark.parametrize("payload", EXAMPLES, ids=[example["name"] for example in MESSAGE["examples"]])
def test_la_funcion_acepta_los_ejemplos_del_contrato(payload: dict) -> None:
    event = parse_event(payload)

    assert str(event.event_id) == payload["event_id"]
    assert event.traveler_email == payload["data"]["traveler_email"]


@pytest.mark.parametrize(
    ("model", "schema_name"),
    [
        (ItineraryCreatedEventSchema, "ItineraryCreatedEventPayload"),
        (ItineraryCreatedDataSchema, "ItineraryCreatedData"),
    ],
)
def test_la_funcion_no_exige_campos_que_el_contrato_no_garantiza(model: type, schema_name: str) -> None:
    assert required_by_function(model) <= set(SCHEMAS[schema_name]["required"])


def test_traveler_email_nulo_es_valido_como_dice_el_contrato() -> None:
    assert "null" in SCHEMAS["ItineraryCreatedData"]["properties"]["traveler_email"]["type"]
    payload = {**EXAMPLES[0], "data": {**EXAMPLES[0]["data"], "traveler_email": None}}

    assert parse_event(payload).traveler_email is None


def test_la_funcion_ignora_campos_nuevos_compatibles() -> None:
    """Agregar un campo opcional no es un cambio incompatible: no requiere event_version 2."""
    payload = {**EXAMPLES[0], "nuevo_campo": "x", "data": {**EXAMPLES[0]["data"], "otro": 1}}

    assert str(parse_event(payload).event_id) == EXAMPLES[0]["event_id"]


@pytest.mark.parametrize("field", ["event_type", "event_version", "producer"])
def test_los_valores_fijos_del_contrato_son_los_que_acepta_la_funcion(field: str) -> None:
    expected = SCHEMAS["ItineraryCreatedEventPayload"]["properties"][field]["const"]

    assert EXAMPLES[0][field] == expected
    parse_event({**EXAMPLES[0], field: expected})


def test_otra_version_del_evento_se_rechaza() -> None:
    """Un cambio incompatible llega con otra event_version: la v1 de la función no lo procesa."""
    with pytest.raises(InvalidEventError):
        parse_event({**EXAMPLES[0], "event_version": 2})


def test_una_fecha_sin_zona_horaria_viola_el_contrato_y_se_rechaza() -> None:
    """date-time en AsyncAPI (RFC 3339) exige zona horaria, como ADR-017."""
    payload = {**EXAMPLES[0], "data": {**EXAMPLES[0]["data"], "travel_date": "2026-12-15T08:00:00"}}

    with pytest.raises(InvalidEventError):
        parse_event(payload)
