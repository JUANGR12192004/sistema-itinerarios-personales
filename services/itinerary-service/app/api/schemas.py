"""Esquemas Pydantic de entrada y salida de la API de Itinerary Service."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateItineraryRequest(BaseModel):
    traveler_name: str = Field(..., min_length=1)
    traveler_email: str | None = None
    departure_airport_id: int = Field(..., gt=0)
    arrival_airport_id: int = Field(..., gt=0)
    travel_date: datetime
    duration_minutes: int = Field(..., gt=0)


class UpdateItineraryRequest(BaseModel):
    traveler_name: str = Field(..., min_length=1)
    traveler_email: str | None = None
    departure_airport_id: int = Field(..., gt=0)
    arrival_airport_id: int = Field(..., gt=0)
    travel_date: datetime
    duration_minutes: int = Field(..., gt=0)


class ItineraryResponse(BaseModel):
    """Representa un itinerario tal como lo ve el cliente de la API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    traveler_name: str
    traveler_email: str | None
    departure_airport_id: int
    arrival_airport_id: int
    travel_date: datetime
    duration_minutes: int
    created_at: datetime
    updated_at: datetime
