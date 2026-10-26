"""DTO externo: la forma exacta en que API Colombia envía un aeropuerto.

Un DTO (Data Transfer Object) solo transporta datos. Este modelo refleja el contrato
del proveedor, con sus nombres y defectos, para que no se filtren al dominio.
Pydantic ignora los campos que no declaramos (descripciones, población, etc.).
"""

from pydantic import BaseModel, ConfigDict, Field


class ApiColombiaNamedEntityDto(BaseModel):
    """Objeto anidado del que solo usamos el nombre (city, department)."""

    model_config = ConfigDict(extra="ignore")

    name: str


class ApiColombiaAirportDto(BaseModel):
    """Aeropuerto tal como lo envía API Colombia en /Airport y /Airport/{id}."""

    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    iata_code: str | None = Field(default=None, alias="iataCode")
    oaci_code: str | None = Field(default=None, alias="oaciCode")
    type: str
    # API Colombia escribe "deparmentId" (sin la t). El error se queda aquí, en el DTO.
    department_id: int | None = Field(default=None, alias="deparmentId")
    department: ApiColombiaNamedEntityDto
    city_id: int | None = Field(default=None, alias="cityId")
    city: ApiColombiaNamedEntityDto
    # Pueden venir intercambiadas: el mapper las corrige.
    latitude: float
    longitude: float
