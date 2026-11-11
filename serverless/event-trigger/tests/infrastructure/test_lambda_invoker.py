"""Pruebas del adaptador HTTP que invoca la función, con respx (sin la función real).

Las respuestas simuladas copian las que dio el RIE real en la demostración de la 6A
(ADR-028): los errores de la función también llegan con HTTP 200.
"""

import json

import httpx
import pytest
import respx

from app.application.invocation import InvocationOutcome
from app.infrastructure.lambda_invoker import LambdaFunctionInvoker

URL = "http://function.local:9000/2015-03-31/functions/function/invocations"
EVENT = {"event_id": "7d9f1c2e-4b5a-4e8f-9a1b-2c3d4e5f6a7b", "event_type": "itinerary.created"}


@pytest.fixture
def invoker():
    invoker = LambdaFunctionInvoker(URL, timeout_seconds=2.0)
    yield invoker
    invoker.close()


def rie_error(error_type: str, message: str = "algo falló") -> dict:
    return {"errorMessage": message, "errorType": error_type, "requestId": "r-1", "stackTrace": []}


@respx.mock
def test_envia_el_evento_como_cuerpo_json(invoker):
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"status": "PROCESSED"}))

    invoker.invoke(EVENT)

    assert json.loads(route.calls.last.request.content) == EVENT


@respx.mock
@pytest.mark.parametrize("status", ["PROCESSED", "ALREADY_PROCESSED"])
def test_procesado_o_duplicado_es_exito(invoker, status):
    respx.post(URL).mock(return_value=httpx.Response(200, json={"status": status, "event_id": "x"}))

    result = invoker.invoke(EVENT)

    assert result.outcome is InvocationOutcome.SUCCESS
    assert result.detail == status


@respx.mock
def test_rejected_es_rechazo_con_el_motivo(invoker):
    respx.post(URL).mock(
        return_value=httpx.Response(200, json={"status": "REJECTED", "reason": "event_version no soportada"})
    )

    result = invoker.invoke(EVENT)

    assert result.outcome is InvocationOutcome.REJECTED
    assert result.detail == "event_version no soportada"


@respx.mock
def test_transient_error_con_http_200_es_fallo_de_infraestructura(invoker):
    respx.post(URL).mock(return_value=httpx.Response(200, json=rie_error("TransientError")))

    result = invoker.invoke(EVENT)

    assert result.outcome is InvocationOutcome.INFRASTRUCTURE_ERROR
    assert "TransientError" in result.detail


@respx.mock
@pytest.mark.parametrize("error_type", ["KeyError", "ProgrammingError", "Runtime.UnmarshalError"])
def test_otro_error_type_es_error_de_la_funcion(invoker, error_type):
    respx.post(URL).mock(return_value=httpx.Response(200, json=rie_error(error_type)))

    result = invoker.invoke(EVENT)

    assert result.outcome is InvocationOutcome.FUNCTION_ERROR
    assert error_type in result.detail


@respx.mock
@pytest.mark.parametrize("status_code", [500, 502, 503])
def test_http_5xx_es_fallo_de_infraestructura(invoker, status_code):
    respx.post(URL).mock(return_value=httpx.Response(status_code, text="error"))

    assert invoker.invoke(EVENT).outcome is InvocationOutcome.INFRASTRUCTURE_ERROR


@respx.mock
@pytest.mark.parametrize("status_code", [400, 404, 413])
def test_otro_codigo_http_es_error_de_la_funcion(invoker, status_code):
    respx.post(URL).mock(return_value=httpx.Response(status_code, text="error"))

    assert invoker.invoke(EVENT).outcome is InvocationOutcome.FUNCTION_ERROR


@respx.mock
@pytest.mark.parametrize(
    "content",
    [b"no es json", b"[1, 2]", json.dumps({"status": "DESCONOCIDO"}).encode(), b"{}"],
)
def test_respuesta_que_no_se_entiende_es_error_de_la_funcion(invoker, content):
    respx.post(URL).mock(return_value=httpx.Response(200, content=content))

    assert invoker.invoke(EVENT).outcome is InvocationOutcome.FUNCTION_ERROR


@respx.mock
def test_timeout_de_la_funcion_en_el_rie_es_fallo_de_infraestructura(invoker):
    """El RIE informa el timeout de la función con HTTP 200 y texto plano (no JSON)."""
    respx.post(URL).mock(return_value=httpx.Response(200, text="Task timed out after 10.00 seconds"))

    result = invoker.invoke(EVENT)

    assert result.outcome is InvocationOutcome.INFRASTRUCTURE_ERROR
    assert result.detail == "Task timed out after 10.00 seconds"


@respx.mock
def test_sin_conexion_con_la_funcion_es_fallo_de_infraestructura(invoker):
    respx.post(URL).mock(side_effect=httpx.ConnectError("connection refused"))

    result = invoker.invoke(EVENT)

    assert result.outcome is InvocationOutcome.INFRASTRUCTURE_ERROR
    assert "ConnectError" in result.detail


@respx.mock
def test_timeout_de_la_invocacion_es_fallo_de_infraestructura(invoker):
    respx.post(URL).mock(side_effect=httpx.ReadTimeout("timed out"))

    result = invoker.invoke(EVENT)

    assert result.outcome is InvocationOutcome.INFRASTRUCTURE_ERROR
    assert "no respondió" in result.detail
