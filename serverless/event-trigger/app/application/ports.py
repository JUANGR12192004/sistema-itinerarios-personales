"""Puertos de la capa de aplicación del Event Trigger."""

from abc import ABC, abstractmethod
from typing import Any

from app.application.invocation import InvocationResult


class FunctionInvoker(ABC):
    """Invoca SendNotificationFunction con un evento.

    Implementado por LambdaFunctionInvoker (HTTP contra el RIE) y por fakes en las pruebas.
    Nunca lanza excepciones por fallos de la invocación: los clasifica en InvocationResult.
    """

    @abstractmethod
    def invoke(self, event: Any) -> InvocationResult:
        """Invoca la función con el evento (ya leído como JSON) y clasifica la respuesta."""
