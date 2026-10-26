"""Proveedor falso de aeropuertos para probar casos de uso y rutas sin API Colombia."""

from app.application.ports import AirportProvider
from app.domain import Airport, AirportNotFoundError, Coordinates


class FakeAirportProvider(AirportProvider):
    """Implementa el puerto con datos en memoria.

    - airports: aeropuertos que "existen".
    - error: si se indica, todas las consultas lanzan esa excepción.
    - calls: registra las llamadas, para comprobar si el proveedor fue consultado.
    """

    def __init__(self, airports: list[Airport] | None = None, error: Exception | None = None) -> None:
        self._airports = airports if airports is not None else sample_airports()
        self._error = error
        self.calls: list[str] = []

    async def list_airports(self) -> list[Airport]:
        self.calls.append("list_airports")
        if self._error:
            raise self._error
        return list(self._airports)

    async def get_airport_by_id(self, airport_id: int) -> Airport:
        self.calls.append(f"get_airport_by_id:{airport_id}")
        if self._error:
            raise self._error
        for airport in self._airports:
            if airport.id == airport_id:
                return airport
        raise AirportNotFoundError(airport_id)


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
