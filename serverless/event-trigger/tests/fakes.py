"""Implementaciones falsas y ayudas para probar el trigger sin RabbitMQ ni la función."""

from typing import Any

from app.application.invocation import InvocationOutcome, InvocationResult
from app.application.ports import FunctionInvoker

SUCCESS = InvocationResult(InvocationOutcome.SUCCESS, "PROCESSED")
REJECTED = InvocationResult(InvocationOutcome.REJECTED, "El evento no cumple el contrato v1")
INFRASTRUCTURE_ERROR = InvocationResult(
    InvocationOutcome.INFRASTRUCTURE_ERROR, "errorType=TransientError: base de datos no disponible"
)
FUNCTION_ERROR = InvocationResult(InvocationOutcome.FUNCTION_ERROR, "errorType=KeyError: 'data'")


class ScriptedInvoker(FunctionInvoker):
    """Devuelve los resultados en el orden dado; al final repite el último."""

    def __init__(self, *results: InvocationResult) -> None:
        self._results = list(results)
        self.calls: list[Any] = []

    def invoke(self, event: Any) -> InvocationResult:
        self.calls.append(event)
        if len(self._results) > 1:
            return self._results.pop(0)
        return self._results[0]


class SleepRecorder:
    """Reemplaza la espera real: solo registra cuántos segundos se habría esperado."""

    def __init__(self) -> None:
        self.waits: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)
