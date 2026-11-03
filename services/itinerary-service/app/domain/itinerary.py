"""Entidad Itinerary: raíz de agregado del contexto de planificación de itinerarios."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.exceptions import InvalidItineraryError


def _validate_fields(
    traveler_name: str,
    departure_airport_id: int,
    arrival_airport_id: int,
    travel_date: datetime,
    duration_minutes: int,
) -> None:
    """Valida las reglas estructurales del itinerario (aplican en create y en update)."""
    if not traveler_name or not traveler_name.strip():
        raise InvalidItineraryError("El nombre del viajero no puede estar vacío.")
    if travel_date.tzinfo is None:
        raise InvalidItineraryError("La fecha de viaje debe incluir zona horaria.")
    if departure_airport_id == arrival_airport_id:
        raise InvalidItineraryError(
            "El aeropuerto de salida y el de llegada deben ser diferentes."
        )
    if duration_minutes <= 0:
        raise InvalidItineraryError(
            "La duración del vuelo debe ser mayor que cero minutos."
        )


@dataclass
class Itinerary:
    """Raíz de agregado del contexto de planificación de itinerarios.

    Usa create() para construir instancias nuevas y update() para modificarlas.
    No instanciar directamente con el constructor del dataclass desde fuera del dominio.
    """

    id: UUID
    traveler_name: str
    departure_airport_id: int
    arrival_airport_id: int
    travel_date: datetime
    duration_minutes: int
    traveler_email: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        traveler_name: str,
        departure_airport_id: int,
        arrival_airport_id: int,
        travel_date: datetime,
        duration_minutes: int,
        traveler_email: str | None = None,
    ) -> Itinerary:
        """Crea un itinerario nuevo aplicando todas las reglas del dominio.

        Regla extra de creación: la fecha de viaje no puede estar en el pasado.
        """
        _validate_fields(
            traveler_name, departure_airport_id, arrival_airport_id,
            travel_date, duration_minutes,
        )
        if travel_date <= datetime.now(timezone.utc):
            raise InvalidItineraryError(
                "La fecha de viaje no puede estar en el pasado."
            )
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            traveler_name=traveler_name.strip(),
            departure_airport_id=departure_airport_id,
            arrival_airport_id=arrival_airport_id,
            travel_date=travel_date,
            duration_minutes=duration_minutes,
            traveler_email=traveler_email,
            created_at=now,
            updated_at=now,
        )

    def update(
        self,
        traveler_name: str,
        departure_airport_id: int,
        arrival_airport_id: int,
        travel_date: datetime,
        duration_minutes: int,
        traveler_email: str | None = None,
    ) -> None:
        """Actualiza los campos del itinerario.

        No verifica que la fecha esté en el futuro: esa regla solo aplica al crear.
        """
        _validate_fields(
            traveler_name, departure_airport_id, arrival_airport_id,
            travel_date, duration_minutes,
        )
        self.traveler_name = traveler_name.strip()
        self.departure_airport_id = departure_airport_id
        self.arrival_airport_id = arrival_airport_id
        self.travel_date = travel_date
        self.duration_minutes = duration_minutes
        self.traveler_email = traveler_email
        self.updated_at = datetime.now(timezone.utc)
