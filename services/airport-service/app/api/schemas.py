"""Esquemas Pydantic de las respuestas HTTP (el contrato público de Airport Service).

Se separan de las entidades del dominio para que un cambio en la API no obligue
a cambiar el dominio, y viceversa.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domain import Airport, Coordinates


class CoordinatesResponse(BaseModel):
    latitude: float = Field(examples=[4.4532428642135])
    longitude: float = Field(examples=[-75.7659806671205])

    @classmethod
    def from_domain(cls, coordinates: Coordinates) -> "CoordinatesResponse":
        return cls(latitude=coordinates.latitude, longitude=coordinates.longitude)


class AirportResponse(BaseModel):
    id: int = Field(examples=[1])
    name: str = Field(examples=["Aeropuerto Internacional El Edén"])
    iata_code: str | None = Field(examples=["AXM"])
    oaci_code: str | None = Field(examples=["SKAR"])
    type: str = Field(examples=["Internacional"])
    city: str = Field(examples=["Armenia"])
    department: str = Field(examples=["Quindío"])
    coordinates: CoordinatesResponse | None = Field(description="null si la ubicación es desconocida")

    @classmethod
    def from_domain(cls, airport: Airport) -> "AirportResponse":
        return cls(
            id=airport.id,
            name=airport.name,
            iata_code=airport.iata_code,
            oaci_code=airport.oaci_code,
            type=airport.type,
            city=airport.city,
            department=airport.department,
            coordinates=CoordinatesResponse.from_domain(airport.coordinates) if airport.coordinates else None,
        )


class MapDataResponse(BaseModel):
    """Datos en formato de columnas, listos para un trazo scattergeo de Plotly.

    La posición i de cada arreglo corresponde al mismo aeropuerto.
    """

    count: int = Field(examples=[2])
    ids: list[int] = Field(examples=[[1, 9]])
    names: list[str] = Field(examples=[["Aeropuerto Internacional El Edén", "Aeropuerto Internacional José María Córdova"]])
    iata_codes: list[str | None] = Field(examples=[["AXM", "MDE"]])
    cities: list[str] = Field(examples=[["Armenia", "Rionegro"]])
    departments: list[str] = Field(examples=[["Quindío", "Antioquia"]])
    types: list[str] = Field(examples=[["Internacional", "Internacional"]])
    latitudes: list[float] = Field(examples=[[4.4532, 6.1645]])
    longitudes: list[float] = Field(examples=[[-75.7659, -75.4231]])

    @classmethod
    def from_domain(cls, airports: list[Airport]) -> "MapDataResponse":
        # El caso de uso ya excluye los aeropuertos sin coordenadas; aquí se vuelve a
        # comprobar porque un mapa no puede dibujar un punto sin latitud ni longitud.
        located = [(airport, airport.coordinates) for airport in airports if airport.coordinates is not None]
        return cls(
            count=len(located),
            ids=[airport.id for airport, _ in located],
            names=[airport.name for airport, _ in located],
            iata_codes=[airport.iata_code for airport, _ in located],
            cities=[airport.city for airport, _ in located],
            departments=[airport.department for airport, _ in located],
            types=[airport.type for airport, _ in located],
            latitudes=[coordinates.latitude for _, coordinates in located],
            longitudes=[coordinates.longitude for _, coordinates in located],
        )


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = Field(examples=["airport-service"])


class ErrorBody(BaseModel):
    code: str = Field(examples=["AIRPORT_NOT_FOUND"])
    message: str = Field(examples=["El aeropuerto con id 999 no existe"])
    details: dict[str, Any] = Field(default_factory=dict, examples=[{"airport_id": 999}])


class ErrorResponse(BaseModel):
    """Formato único de error de todos los servicios (CLAUDE.md, sección 10.2)."""

    error: ErrorBody
    correlation_id: str = Field(examples=["3f2a9c1e-6b7d-4c2a-9e1f-0a1b2c3d4e5f"])
