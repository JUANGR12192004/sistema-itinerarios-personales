"""Verifica que docs/asyncapi/asyncapi.yaml nombra la misma topología que declara el trigger.

Compara el texto del archivo (sin una librería de YAML, que el trigger no necesita): si alguien
renombra la cola, la DLX o la DLQ en el código sin actualizar AsyncAPI (o al revés), falla.
El contrato del evento lo verifica Itinerary Service (tests/application/test_asyncapi_contract.py).
"""

from pathlib import Path

import pytest

from app.infrastructure.rabbitmq.topology import (
    DEAD_LETTER_EXCHANGE,
    DEAD_LETTER_QUEUE,
    EXCHANGE,
    QUEUE_NOTIFICATIONS,
    ROUTING_KEY_ITINERARY_CREATED,
)

ASYNCAPI_PATH = Path(__file__).resolve().parents[3] / "docs" / "asyncapi" / "asyncapi.yaml"


@pytest.fixture(scope="module")
def asyncapi() -> str:
    return ASYNCAPI_PATH.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "fragment",
    [
        f"address: {QUEUE_NOTIFICATIONS}\n",
        f"address: {DEAD_LETTER_QUEUE}\n",
        f"address: {ROUTING_KEY_ITINERARY_CREATED}\n",
        f"name: {EXCHANGE}\n",
        f"`{DEAD_LETTER_EXCHANGE}`",
    ],
)
def test_la_topologia_del_trigger_esta_en_asyncapi(asyncapi, fragment):
    assert fragment in asyncapi


def test_asyncapi_documenta_la_operacion_de_recepcion_y_el_reprocesamiento(asyncapi):
    assert "action: receive" in asyncapi
    assert "python -m app.replay_dlq" in asyncapi
