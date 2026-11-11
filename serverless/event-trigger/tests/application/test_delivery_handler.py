"""Pruebas de la política de entrega del Event Trigger (ADR-031), sin RabbitMQ ni la función."""

import json

import pytest

from app.application.delivery_handler import Decision, DeliveryHandler, RetryPolicy
from tests.fakes import (
    FUNCTION_ERROR,
    INFRASTRUCTURE_ERROR,
    REJECTED,
    SUCCESS,
    ScriptedInvoker,
    SleepRecorder,
)

POLICY = RetryPolicy(
    infrastructure_attempts=3,
    function_error_attempts=3,
    backoff_seconds=1.0,
    max_backoff_seconds=8.0,
    requeue_delay_seconds=10.0,
)
BODY = json.dumps({"event_id": "7d9f1c2e-4b5a-4e8f-9a1b-2c3d4e5f6a7b", "event_type": "itinerary.created"}).encode()


def handle(*results, body: bytes = BODY, policy: RetryPolicy = POLICY):
    invoker = ScriptedInvoker(*results)
    sleep = SleepRecorder()
    decision = DeliveryHandler(invoker, policy, sleep).handle(body, message_id="m-1")
    return decision, invoker, sleep


# ——— Éxito ———

def test_exito_confirma_el_mensaje_sin_esperar():
    decision, invoker, sleep = handle(SUCCESS)

    assert decision is Decision.ACK
    assert invoker.calls == [json.loads(BODY)]  # la función recibe el evento ya leído como JSON
    assert sleep.waits == []


# ——— Fallos permanentes: a la DLQ sin reintentar ———

def test_evento_rechazado_por_la_funcion_va_a_la_dlq_sin_reintentar():
    decision, invoker, sleep = handle(REJECTED)

    assert decision is Decision.REJECT
    assert len(invoker.calls) == 1
    assert sleep.waits == []


@pytest.mark.parametrize("body", [b"esto no es JSON", b"{incompleto", b"\xff\xfe"])
def test_mensaje_que_no_es_json_va_a_la_dlq_sin_invocar_la_funcion(body):
    decision, invoker, _ = handle(SUCCESS, body=body)

    assert decision is Decision.REJECT
    assert invoker.calls == []


def test_json_que_no_es_objeto_se_entrega_a_la_funcion_para_que_decida():
    decision, invoker, _ = handle(REJECTED, body=b'"hola"')

    assert invoker.calls == ["hola"]
    assert decision is Decision.REJECT


# ——— Fallos de infraestructura: sin límite, nunca a la DLQ ———

def test_fallo_de_infraestructura_persistente_devuelve_el_mensaje_a_la_cola():
    decision, invoker, sleep = handle(INFRASTRUCTURE_ERROR)

    assert decision is Decision.REQUEUE  # nunca REJECT: no va a la DLQ
    assert len(invoker.calls) == 3
    assert sleep.waits == [1.0, 2.0, 10.0]  # backoff entre intentos y pausa antes de devolverlo


def test_fallo_de_infraestructura_pasajero_se_resuelve_con_un_reintento():
    decision, invoker, sleep = handle(INFRASTRUCTURE_ERROR, SUCCESS)

    assert decision is Decision.ACK
    assert len(invoker.calls) == 2
    assert sleep.waits == [1.0]


# ——— Errores de la función: reintentos limitados y después a la DLQ ———

def test_error_de_la_funcion_persistente_va_a_la_dlq_tras_los_reintentos():
    decision, invoker, sleep = handle(FUNCTION_ERROR)

    assert decision is Decision.REJECT
    assert len(invoker.calls) == 3
    assert sleep.waits == [1.0, 2.0]


def test_error_de_la_funcion_pasajero_se_resuelve_con_un_reintento():
    decision, invoker, _ = handle(FUNCTION_ERROR, SUCCESS)

    assert decision is Decision.ACK
    assert len(invoker.calls) == 2


def test_los_dos_tipos_de_fallo_se_cuentan_por_separado():
    """Dos errores de la función no agotan los intentos de infraestructura, ni al revés."""
    decision, invoker, _ = handle(
        FUNCTION_ERROR, INFRASTRUCTURE_ERROR, FUNCTION_ERROR, INFRASTRUCTURE_ERROR, SUCCESS
    )

    assert decision is Decision.ACK
    assert len(invoker.calls) == 5


def test_con_un_solo_intento_devuelve_el_mensaje_enseguida_tras_la_pausa():
    policy = RetryPolicy(infrastructure_attempts=1, requeue_delay_seconds=5.0)

    decision, invoker, sleep = handle(INFRASTRUCTURE_ERROR, policy=policy)

    assert decision is Decision.REQUEUE
    assert len(invoker.calls) == 1
    assert sleep.waits == [5.0]


# ——— RetryPolicy ———

def test_el_backoff_se_duplica_hasta_el_maximo():
    assert [POLICY.backoff(n) for n in range(1, 6)] == [1.0, 2.0, 4.0, 8.0, 8.0]


@pytest.mark.parametrize("field", ["infrastructure_attempts", "function_error_attempts"])
def test_los_intentos_deben_ser_al_menos_uno(field):
    with pytest.raises(ValueError):
        RetryPolicy(**{field: 0})
