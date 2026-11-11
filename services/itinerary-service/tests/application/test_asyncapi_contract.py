"""Verifica que docs/asyncapi/asyncapi.yaml describe el mismo evento que publica el código.

Si alguien cambia ItineraryCreatedEvent sin actualizar AsyncAPI (o al revés), esta prueba falla.
PyYAML llega instalado con uvicorn[standard]; si faltara, la prueba se omite.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.application.events import ItineraryCreatedEvent
from app.domain.itinerary import Itinerary
from app.infrastructure.messaging.topology import EXCHANGE, ROUTING_KEY_ITINERARY_CREATED

yaml = pytest.importorskip("yaml")

ASYNCAPI_PATH = Path(__file__).resolve().parents[4] / "docs" / "asyncapi" / "asyncapi.yaml"


@pytest.fixture(scope="module")
def spec() -> dict:
    with ASYNCAPI_PATH.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


@pytest.fixture(scope="module")
def payload() -> dict:
    itinerary = Itinerary.create(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=datetime.now(timezone.utc) + timedelta(days=30),
        duration_minutes=75,
    )
    return ItineraryCreatedEvent.from_itinerary(itinerary).to_dict()


def test_campos_del_evento_coinciden_con_asyncapi(spec, payload):
    schema = spec["components"]["schemas"]["ItineraryCreatedEventPayload"]

    assert set(schema["properties"]) == set(payload)
    assert set(schema["required"]) == set(payload)


def test_campos_de_data_coinciden_con_asyncapi(spec, payload):
    schema = spec["components"]["schemas"]["ItineraryCreatedData"]

    assert set(schema["properties"]) == set(payload["data"])
    assert set(schema["required"]) == set(payload["data"])


def test_constantes_del_evento_coinciden(spec, payload):
    properties = spec["components"]["schemas"]["ItineraryCreatedEventPayload"]["properties"]

    assert properties["event_type"]["const"] == payload["event_type"]
    assert properties["event_version"]["const"] == payload["event_version"]
    assert properties["producer"]["const"] == payload["producer"]


def test_el_ejemplo_tiene_la_forma_del_evento(spec, payload):
    example = spec["components"]["messages"]["ItineraryCreatedEvent"]["examples"][0]["payload"]

    assert set(example) == set(payload)
    assert set(example["data"]) == set(payload["data"])


def test_exchange_y_routing_key_coinciden_con_asyncapi(spec):
    """Solo la parte de la topología que pertenece al productor (ADR-032).
    La cola de notificaciones la declara y la verifica el Event Trigger."""
    channel = spec["channels"]["itineraryCreated"]

    assert channel["address"] == ROUTING_KEY_ITINERARY_CREATED
    assert channel["bindings"]["amqp"]["exchange"]["name"] == EXCHANGE
