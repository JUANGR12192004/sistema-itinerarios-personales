"""ItineraryCreatedEvent tal como lo lee el contexto de Notificaciones.

Es el mismo evento de integración que publica Itinerary Service (contrato v1, ADR-020),
pero modelado aquí con solo los datos que necesita la notificación. Notificaciones no
importa código de Itinerary Service: los dos contextos solo comparten el contrato publicado.
El adaptador de entrada (app/event_schema.py) valida el JSON y construye este objeto.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ItineraryCreatedEvent:
    """Datos del evento `itinerary.created` (versión 1) que usa la función."""

    event_id: UUID
    occurred_at: datetime
    correlation_id: str
    itinerary_id: UUID
    traveler_name: str
    traveler_email: str | None
    departure_airport_id: int
    arrival_airport_id: int
    travel_date: datetime
    duration_minutes: int
