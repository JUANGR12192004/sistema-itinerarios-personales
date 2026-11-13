"""Política de entrega del Event Trigger: qué hacer con cada mensaje (ADR-031).

Para cada mensaje de la cola decide una de tres acciones:

    ACK      → el mensaje se procesó: RabbitMQ lo borra de la cola.
    REJECT   → fallo permanente: se rechaza sin reencolar y RabbitMQ lo envía a la DLQ.
    REQUEUE  → fallo de infraestructura: vuelve a la cola para intentarlo de nuevo, sin límite.

| Resultado de la invocación      | Reintentos dentro del trigger       | Si se agotan          |
|---------------------------------|-------------------------------------|-----------------------|
| SUCCESS                         | —                                   | ACK                   |
| REJECTED (o el mensaje no es JSON) | ninguno: reintentar no lo arregla | REJECT → DLQ          |
| INFRASTRUCTURE_ERROR            | `infrastructure_attempts`, con espera | pausa y REQUEUE (nunca a la DLQ) |
| FUNCTION_ERROR                  | `function_error_attempts`, con espera | REJECT → DLQ          |

Es el mismo criterio de ADR-027 (Outbox Relay) aplicado al consumidor: lo temporal se
reintenta sin límite y lo permanente se aparta para que no bloquee a los demás.

No conoce RabbitMQ ni HTTP: recibe el cuerpo del mensaje, usa el puerto FunctionInvoker y
devuelve la decisión. El consumidor de RabbitMQ la aplica. `sleep` se inyecta: el
consumidor pasa `connection.sleep` de pika (atiende los heartbeats mientras espera) y las
pruebas pasan una función que solo registra las esperas.
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.application.invocation import InvocationOutcome
from app.application.ports import FunctionInvoker
from app.metrics import NOTIFICATIONS_DISPATCHED

logger = logging.getLogger(__name__)


class Decision(StrEnum):
    """Acción que el consumidor aplica al mensaje en RabbitMQ."""

    ACK = "ACK"
    REJECT = "REJECT"
    REQUEUE = "REQUEUE"


@dataclass(frozen=True)
class RetryPolicy:
    """Valores de la política de reintentos (variables TRIGGER_* del .env)."""

    infrastructure_attempts: int = 3
    function_error_attempts: int = 3
    backoff_seconds: float = 1.0
    max_backoff_seconds: float = 8.0
    requeue_delay_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.infrastructure_attempts < 1 or self.function_error_attempts < 1:
            raise ValueError("Los intentos deben ser al menos 1")

    def backoff(self, failures: int) -> float:
        """Exponential backoff: 1 s, 2 s, 4 s... (con los valores por defecto), hasta el máximo."""
        return min(self.backoff_seconds * 2 ** (failures - 1), self.max_backoff_seconds)


class DeliveryHandler:
    """Invoca la función con el evento de un mensaje y decide ACK, REJECT o REQUEUE."""

    def __init__(
        self,
        invoker: FunctionInvoker,
        policy: RetryPolicy,
        sleep: Callable[[float], None],
    ) -> None:
        self._invoker = invoker
        self._policy = policy
        self._sleep = sleep

    def handle(
        self, body: bytes, message_id: str | None = None, traceparent: str | None = None
    ) -> Decision:
        try:
            event = json.loads(body.decode("utf-8"))
        except ValueError as exc:  # incluye UnicodeDecodeError y JSONDecodeError
            # Fallo PERMANENTE: no se invoca la función (el RIE fallaría con Runtime.UnmarshalError).
            # logger.error y no logger.exception: es un caso esperado y el traceback de json.loads no
            # ayuda a diagnosticar; el motivo ya va en el mensaje (sin el contenido del mensaje).
            logger.error(
                "Mensaje rechazado sin invocar la función (no es JSON): message_id=%s error=%s. Va a la DLQ",
                message_id,
                exc,
            )
            NOTIFICATIONS_DISPATCHED.labels(outcome="rejected").inc()
            return Decision.REJECT

        label = _event_label(event, message_id)
        infrastructure_failures = 0
        function_failures = 0

        while True:
            result = self._invoker.invoke(event, traceparent=traceparent)
            # Registra cada intento de invocación con su resultado (ADR-038)
            NOTIFICATIONS_DISPATCHED.labels(outcome=result.outcome.value.lower()).inc()

            if result.outcome is InvocationOutcome.SUCCESS:
                logger.info("Evento procesado (%s): %s. ACK", result.detail, label)
                return Decision.ACK

            if result.outcome is InvocationOutcome.REJECTED:
                logger.error(
                    "La función rechazó el evento (fallo permanente): %s motivo=%s. Va a la DLQ",
                    label,
                    result.detail,
                )
                return Decision.REJECT

            if result.outcome is InvocationOutcome.INFRASTRUCTURE_ERROR:
                infrastructure_failures += 1
                if infrastructure_failures >= self._policy.infrastructure_attempts:
                    logger.warning(
                        "Fallo de infraestructura en %d intentos: %s (%s). "
                        "Se devuelve a la cola en %.1f s y se reintentará (no va a la DLQ)",
                        infrastructure_failures,
                        label,
                        result.detail,
                        self._policy.requeue_delay_seconds,
                    )
                    self._sleep(self._policy.requeue_delay_seconds)
                    return Decision.REQUEUE
                wait = self._policy.backoff(infrastructure_failures)
                attempts = self._policy.infrastructure_attempts
                failures = infrastructure_failures
            else:  # FUNCTION_ERROR
                function_failures += 1
                if function_failures >= self._policy.function_error_attempts:
                    logger.error(
                        "Error de la función en %d intentos: %s (%s). Va a la DLQ para no bloquear la cola",
                        function_failures,
                        label,
                        result.detail,
                    )
                    return Decision.REJECT
                wait = self._policy.backoff(function_failures)
                attempts = self._policy.function_error_attempts
                failures = function_failures

            logger.warning(
                "Intento %d de %d fallido (%s): %s. Nuevo intento en %.1f s",
                failures,
                attempts,
                result.detail,
                label,
                wait,
            )
            self._sleep(wait)


def _event_label(event: Any, message_id: str | None) -> str:
    """Identifica el mensaje en los logs: event_id del cuerpo, o el message_id de AMQP."""
    event_id = event.get("event_id") if isinstance(event, dict) else None
    return f"event_id={event_id or message_id}"
