"""Decorator que agrega circuit breaker y retry a cualquier AirportProvider.

Patrón Decorator: ResilientAirportProvider implementa el mismo puerto AirportProvider y
envuelve a otro proveedor (el Adapter de API Colombia). Los casos de uso no cambian y el
Adapter tampoco: la resiliencia se agrega "por fuera".

Orden de cada consulta (decisión de la Fase 2):

    circuit breaker → retry con backoff → llamada con timeout (Adapter)

El circuit breaker queda por fuera del retry: una consulta cuenta como UN fallo para el
circuito solo cuando ya se agotaron todos sus reintentos.
"""

from app.application.ports import AirportProvider
from app.domain import Airport
from app.infrastructure.resilience.circuit_breaker import CircuitBreaker
from app.infrastructure.resilience.retry import RetryPolicy


class ResilientAirportProvider(AirportProvider):
    """Implementa AirportProvider delegando en otro proveedor, protegido con circuit breaker y retry."""

    def __init__(self, inner: AirportProvider, circuit_breaker: CircuitBreaker, retry_policy: RetryPolicy) -> None:
        self._inner = inner
        self._circuit_breaker = circuit_breaker
        self._retry_policy = retry_policy

    async def list_airports(self) -> list[Airport]:
        return await self._circuit_breaker.call(lambda: self._retry_policy.run(self._inner.list_airports))

    async def get_airport_by_id(self, airport_id: int) -> Airport:
        return await self._circuit_breaker.call(
            lambda: self._retry_policy.run(lambda: self._inner.get_airport_by_id(airport_id))
        )
