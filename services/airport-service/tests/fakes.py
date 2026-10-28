"""Implementaciones falsas para probar sin API Colombia, sin Redis y sin esperas reales."""

from app.application.ports import AirportProvider
from app.domain import Airport, AirportNotFoundError, Coordinates
from app.infrastructure.cache.store import CacheError, CacheStore


class FakeAirportProvider(AirportProvider):
    """Implementa el puerto con datos en memoria.

    - airports: aeropuertos que "existen".
    - error: si se indica, todas las consultas lanzan esa excepción.
    - fail_next(...): las próximas consultas lanzan esos errores, uno por consulta (proveedor intermitente).
    - calls: registra las llamadas, para comprobar si el proveedor fue consultado.
    """

    def __init__(self, airports: list[Airport] | None = None, error: Exception | None = None) -> None:
        self._airports = airports if airports is not None else sample_airports()
        self.error = error
        self._next_errors: list[Exception] = []
        self.calls: list[str] = []

    def fail_next(self, *errors: Exception) -> None:
        self._next_errors.extend(errors)

    async def list_airports(self) -> list[Airport]:
        self.calls.append("list_airports")
        self._raise_if_failing()
        return list(self._airports)

    async def get_airport_by_id(self, airport_id: int) -> Airport:
        self.calls.append(f"get_airport_by_id:{airport_id}")
        self._raise_if_failing()
        for airport in self._airports:
            if airport.id == airport_id:
                return airport
        raise AirportNotFoundError(airport_id)

    def _raise_if_failing(self) -> None:
        if self._next_errors:
            raise self._next_errors.pop(0)
        if self.error:
            raise self.error


class InMemoryCacheStore(CacheStore):
    """Almacén de caché en un diccionario (reemplaza a Redis en las pruebas).

    - data / ttls: lo guardado y el TTL con que se guardó cada clave.
    - available: en False simula que Redis está caído (lanza CacheError).
    """

    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.available = True

    async def get(self, key: str) -> str | None:
        self._check_available()
        return self.data.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._check_available()
        self.data[key] = value
        self.ttls[key] = ttl_seconds

    def expire(self, key: str) -> None:
        """Simula que la clave venció (Redis la borra al cumplirse su TTL)."""
        self.data.pop(key, None)

    def _check_available(self) -> None:
        if not self.available:
            raise CacheError("Redis no disponible (simulado)")


class FakeClock:
    """Reloj controlado para el circuit breaker: el tiempo solo avanza con advance()."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class RecordingSleep:
    """Reemplaza a asyncio.sleep en el retry: no espera, solo anota cuánto habría esperado."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)


def sample_airports() -> list[Airport]:
    """Tres aeropuertos reales (ya traducidos), desordenados a propósito; uno sin ubicación."""
    return [
        Airport(
            id=9,
            name="Aeropuerto Internacional José María Córdova",
            iata_code="MDE",
            oaci_code="SKRG",
            type="Internacional",
            city="Rionegro",
            department="Antioquia",
            coordinates=Coordinates(latitude=6.1645330006573, longitude=-75.423110000511),
        ),
        Airport(
            id=43,
            name="Aeropuerto del Café",
            iata_code=None,
            oaci_code=None,
            type="En Construccion",
            city="Manizales",
            department="Caldas",
            coordinates=None,
        ),
        Airport(
            id=1,
            name="Aeropuerto Internacional El Edén",
            iata_code="AXM",
            oaci_code="SKAR",
            type="Internacional",
            city="Armenia",
            department="Quindío",
            coordinates=Coordinates(latitude=4.4532428642135, longitude=-75.7659806671205),
        ),
    ]
