"""Circuit breaker (interruptor de circuito).

Si API Colombia falla varias veces seguidas, seguir llamándola solo hace esperar al usuario
(timeouts y reintentos) y le agrega carga a un proveedor que ya tiene problemas.
El circuit breaker funciona como el breaker eléctrico de una casa:

- CLOSED (cerrado): estado normal, las llamadas pasan. Cuenta los fallos seguidos.
- OPEN (abierto): tras failure_threshold fallos seguidos, rechaza las llamadas al instante
  (CircuitOpenError → 503) sin contactar al proveedor, durante recovery_seconds.
- HALF_OPEN (semiabierto): pasado ese tiempo, deja pasar UNA llamada de prueba.
  Si funciona, vuelve a CLOSED; si falla, vuelve a OPEN y espera otra vez.

Solo cuentan como fallo los errores de disponibilidad (incluido el timeout). Un 404 o un 502
significan que el proveedor sí respondió, así que cuentan como éxito y no abren el circuito.
"""

import logging
import time
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TypeVar

from app.application.exceptions import AirportProviderUnavailableError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitOpenError(AirportProviderUnavailableError):
    """El circuito está abierto: se rechaza la llamada sin contactar al proveedor (503)."""


class CircuitBreaker:
    """Protege una dependencia externa cortando las llamadas mientras está fallando.

    - failure_threshold: fallos seguidos que abren el circuito.
    - recovery_seconds: tiempo que el circuito permanece abierto antes de la llamada de prueba.
    - clock: reloj en segundos; las pruebas inyectan uno controlado para no esperar de verdad.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int,
        recovery_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold debe ser al menos 1")
        self._name = name
        self._failure_threshold = failure_threshold
        self._recovery_seconds = recovery_seconds
        self._clock = clock
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._opened_at = 0.0
        self._trial_in_progress = False

    @property
    def state(self) -> CircuitState:
        """Estado actual. Si ya pasó el tiempo de recuperación, el circuito abierto pasa a HALF_OPEN."""
        if self._state is CircuitState.OPEN and self._clock() - self._opened_at >= self._recovery_seconds:
            self._change_state(CircuitState.HALF_OPEN)
        return self._state

    async def call(self, operation: Callable[[], Awaitable[T]]) -> T:
        """Ejecuta la operación si el circuito lo permite y registra si tuvo éxito o falló."""
        state = self.state
        if state is CircuitState.OPEN or (state is CircuitState.HALF_OPEN and self._trial_in_progress):
            raise CircuitOpenError(f"Circuito '{self._name}' abierto: no se contacta al proveedor")

        is_trial = state is CircuitState.HALF_OPEN
        self._trial_in_progress = is_trial
        try:
            result = await operation()
        except AirportProviderUnavailableError:
            self._on_failure()
            raise
        except Exception:
            # El proveedor sí respondió (por ejemplo, un 404): para el circuito es un éxito.
            self._on_success()
            raise
        finally:
            if is_trial:
                self._trial_in_progress = False
        self._on_success()
        return result

    def _on_success(self) -> None:
        self._consecutive_failures = 0
        if self._state is not CircuitState.CLOSED:
            self._change_state(CircuitState.CLOSED)

    def _on_failure(self) -> None:
        self._consecutive_failures += 1
        # En HALF_OPEN basta un fallo de la llamada de prueba para volver a abrir.
        if self._state is CircuitState.HALF_OPEN or self._consecutive_failures >= self._failure_threshold:
            self._opened_at = self._clock()
            if self._state is not CircuitState.OPEN:
                self._change_state(CircuitState.OPEN)

    def _change_state(self, new_state: CircuitState) -> None:
        logger.warning(
            "Circuit breaker '%s': %s -> %s (fallos seguidos: %s)",
            self._name,
            self._state.value,
            new_state.value,
            self._consecutive_failures,
        )
        self._state = new_state
