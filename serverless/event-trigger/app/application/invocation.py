"""Resultado de invocar SendNotificationFunction, ya clasificado (ADR-031).

El adaptador HTTP traduce la respuesta del RIE (código HTTP + cuerpo) a uno de estos
cuatro resultados. La política de reintentos solo conoce estos resultados: no sabe nada
de HTTP, del RIE ni de RabbitMQ.
"""

from dataclasses import dataclass
from enum import StrEnum


class InvocationOutcome(StrEnum):
    """Qué pasó al invocar la función.

    SUCCESS:              la función respondió PROCESSED o ALREADY_PROCESSED.
    REJECTED:             la función respondió REJECTED: el evento no cumple el contrato (permanente).
    INFRASTRUCTURE_ERROR: la función o su base de datos no están disponibles (sin conexión,
                          timeout, HTTP 5xx o errorType TransientError). Temporal.
    FUNCTION_ERROR:       otro errorType o una respuesta que no se entiende; lo más probable
                          es un error de programación.
    """

    SUCCESS = "SUCCESS"
    REJECTED = "REJECTED"
    INFRASTRUCTURE_ERROR = "INFRASTRUCTURE_ERROR"
    FUNCTION_ERROR = "FUNCTION_ERROR"


@dataclass(frozen=True)
class InvocationResult:
    """Resultado clasificado y un detalle legible para el log."""

    outcome: InvocationOutcome
    detail: str
