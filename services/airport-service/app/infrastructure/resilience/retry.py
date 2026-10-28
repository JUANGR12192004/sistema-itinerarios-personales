"""Retry con exponential backoff.

Retry: si una llamada falla por un problema pasajero (el proveedor no responde, da un 5xx
o tarda demasiado), se repite unas pocas veces antes de rendirse.

Exponential backoff: la espera entre intentos se duplica (0.5 s, 1 s, 2 s...) hasta un máximo.
Así se le da tiempo al proveedor para recuperarse y no se le satura con reintentos seguidos.

Solo se reintentan los errores de disponibilidad (AirportProviderUnavailableError, que incluye
el timeout). Un 404 o una respuesta inválida (502) darían el mismo resultado al repetirlos.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.application.exceptions import AirportProviderUnavailableError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryPolicy:
    """Ejecuta una operación asíncrona con reintentos y esperas crecientes.

    - max_attempts: intentos totales (1 = sin reintentos).
    - base_delay: espera antes del primer reintento; se duplica en cada reintento.
    - max_delay: espera máxima entre dos intentos.
    - sleep: función de espera; las pruebas inyectan una que no espera de verdad.
    """

    def __init__(
        self,
        max_attempts: int,
        base_delay: float,
        max_delay: float,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts debe ser al menos 1")
        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._sleep = sleep

    def delay_before_retry(self, retry_number: int) -> float:
        """Espera antes del reintento número retry_number (1, 2, ...): base * 2^(n-1), con tope."""
        return min(self._max_delay, self._base_delay * 2 ** (retry_number - 1))

    async def run(self, operation: Callable[[], Awaitable[T]]) -> T:
        """Ejecuta la operación; si falla por disponibilidad, espera y la repite.

        Si se agotan los intentos, relanza el último error (503 o, si fue un timeout, 504).
        """
        for attempt in range(1, self._max_attempts + 1):
            try:
                return await operation()
            except AirportProviderUnavailableError as error:
                if attempt == self._max_attempts:
                    logger.warning("Se agotaron los %s intentos: %s", self._max_attempts, error)
                    raise
                delay = self.delay_before_retry(attempt)
                logger.warning(
                    "Intento %s de %s falló (%s). Reintentando en %.2f s", attempt, self._max_attempts, error, delay
                )
                await self._sleep(delay)
        # No se llega aquí: el último intento devuelve un resultado o relanza el error.
        raise AssertionError("RetryPolicy.run terminó sin resultado")
