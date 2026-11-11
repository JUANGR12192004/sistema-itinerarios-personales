"""Adaptador que invoca SendNotificationFunction a través de la API de Lambda del RIE (ADR-008).

    POST http://localhost:9000/2015-03-31/functions/function/invocations   (cuerpo = evento)

Clasifica la respuesta en un InvocationResult (ADR-031). El RIE responde HTTP 200 también
cuando la función falla (ADR-028): el error solo se reconoce porque el cuerpo trae
`errorType`. Por eso se revisan el código HTTP y el cuerpo.
"""

import json
from typing import Any

import httpx

from app.application.invocation import InvocationOutcome, InvocationResult
from app.application.ports import FunctionInvoker

# errorType que significan "infraestructura no disponible" (temporal, se reintenta sin límite)
INFRASTRUCTURE_ERROR_TYPES = frozenset({"TransientError"})
# Si la función supera su timeout, el RIE responde HTTP 200 con este TEXTO (no JSON),
# por ejemplo "Task timed out after 10.00 seconds" (comprobado en la 6B). Se trata como
# fallo de infraestructura: lo más probable es que una dependencia no responda.
FUNCTION_TIMEOUT_PREFIX = b"Task timed out"
SUCCESS_STATUSES = frozenset({"PROCESSED", "ALREADY_PROCESSED"})
# Del errorMessage solo se registra la primera línea, hasta este largo (ver _first_line)
MAX_ERROR_DETAIL_LENGTH = 200
REJECTED_STATUS = "REJECTED"


class LambdaFunctionInvoker(FunctionInvoker):
    """Invoca la función por HTTP con httpx. `client` permite inyectar uno de prueba."""

    def __init__(self, invoke_url: str, timeout_seconds: float, client: httpx.Client | None = None) -> None:
        self._invoke_url = invoke_url
        self._timeout_seconds = timeout_seconds
        self._client = client or httpx.Client()

    def invoke(self, event: Any) -> InvocationResult:
        try:
            response = self._client.post(self._invoke_url, json=event, timeout=self._timeout_seconds)
        except httpx.TimeoutException:
            return InvocationResult(
                InvocationOutcome.INFRASTRUCTURE_ERROR,
                f"la función no respondió en {self._timeout_seconds} s",
            )
        except httpx.HTTPError as exc:
            return InvocationResult(
                InvocationOutcome.INFRASTRUCTURE_ERROR,
                f"no se pudo conectar con la función ({type(exc).__name__})",
            )
        return classify_response(response.status_code, response.content)

    def close(self) -> None:
        self._client.close()


def classify_response(status_code: int, content: bytes) -> InvocationResult:
    """Traduce la respuesta del RIE (código HTTP y cuerpo) a un InvocationResult."""
    if status_code >= 500:
        return InvocationResult(InvocationOutcome.INFRASTRUCTURE_ERROR, f"HTTP {status_code} del RIE")
    if status_code != 200:
        return InvocationResult(InvocationOutcome.FUNCTION_ERROR, f"HTTP {status_code} inesperado")
    if content.startswith(FUNCTION_TIMEOUT_PREFIX):
        return InvocationResult(InvocationOutcome.INFRASTRUCTURE_ERROR, content.decode("utf-8", "replace"))

    try:
        body = json.loads(content)
    except ValueError:
        return InvocationResult(InvocationOutcome.FUNCTION_ERROR, "la respuesta no es JSON")
    if not isinstance(body, dict):
        return InvocationResult(InvocationOutcome.FUNCTION_ERROR, "la respuesta no es un objeto JSON")

    error_type = body.get("errorType")
    if error_type is not None:
        detail = f"errorType={error_type}: {_first_line(body.get('errorMessage'))}"
        if error_type in INFRASTRUCTURE_ERROR_TYPES:
            return InvocationResult(InvocationOutcome.INFRASTRUCTURE_ERROR, detail)
        return InvocationResult(InvocationOutcome.FUNCTION_ERROR, detail)

    status = body.get("status")
    if status in SUCCESS_STATUSES:
        return InvocationResult(InvocationOutcome.SUCCESS, status)
    if status == REJECTED_STATUS:
        return InvocationResult(InvocationOutcome.REJECTED, str(body.get("reason")))
    return InvocationResult(InvocationOutcome.FUNCTION_ERROR, f"respuesta desconocida: status={status!r}")


def _first_line(message: object) -> str:
    """Primera línea del errorMessage, recortada.

    Un error de SQLAlchemy trae varias líneas con el SQL y sus PARÁMETROS (por ejemplo, el
    correo del viajero). El trigger solo necesita saber qué pasó; el detalle completo queda en
    el log de la función (`docker logs send-notification-function`).
    """
    lines = str(message or "").strip().splitlines()
    first = lines[0] if lines else ""
    return first if len(first) <= MAX_ERROR_DETAIL_LENGTH else first[:MAX_ERROR_DETAIL_LENGTH] + "…"
