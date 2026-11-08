"""Eventos de integración que publica Itinerary Service.

Un evento de integración es un CONTRATO PÚBLICO entre servicios: otros contextos
(por ejemplo, Notificaciones) dependen de su forma exacta. Por eso:

- Vive en la capa de aplicación y no en el dominio: el dominio no sabe que existen
  otros servicios ni cómo se comunican.
- Tiene una versión (`event_version`). Un cambio incompatible exige una versión nueva.
- Se construye a partir de la entidad `Itinerary`, pero solo expone los datos que
  el contrato promete (no todo el modelo interno).

El contrato completo está en docs/asyncapi/asyncapi.yaml y en CLAUDE.md (sección 11.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, ClassVar
from uuid import UUID, uuid4

from app.domain.itinerary import Itinerary


@dataclass(frozen=True)
class ItineraryCreatedEvent:
    """Hecho de integración: se registró un nuevo itinerario (versión 1 del contrato).

    Es inmutable (frozen) porque un evento describe algo que ya ocurrió.
    """

    EVENT_TYPE: ClassVar[str] = "itinerary.created"
    EVENT_VERSION: ClassVar[int] = 1
    PRODUCER: ClassVar[str] = "itinerary-service"

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

    @classmethod
    def from_itinerary(
        cls, itinerary: Itinerary, correlation_id: str | None = None
    ) -> ItineraryCreatedEvent:
        """Construye el evento a partir del itinerario recién creado.

        Cada evento recibe un `event_id` nuevo: los consumidores lo usan como clave
        de idempotencia para no procesar dos veces el mismo mensaje.
        Si no llega un correlation ID de la solicitud HTTP, se genera uno.
        """
        return cls(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            correlation_id=correlation_id or str(uuid4()),
            itinerary_id=itinerary.id,
            traveler_name=itinerary.traveler_name,
            traveler_email=itinerary.traveler_email,
            departure_airport_id=itinerary.departure_airport_id,
            arrival_airport_id=itinerary.arrival_airport_id,
            travel_date=itinerary.travel_date,
            duration_minutes=itinerary.duration_minutes,
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ItineraryCreatedEvent:
        """Reconstruye el evento desde su forma de contrato (la inversa de `to_dict`).

        Lo usa el Outbox Relay (Fase 5): el evento se guarda como JSON en `outbox_events`
        y se vuelve a convertir en objeto para publicarlo con RabbitMQEventPublisher.

        Raises:
            ValueError: el tipo o la versión no corresponden a este evento, o un valor
                tiene formato inválido.
            KeyError: falta un campo del contrato.
        """
        if payload["event_type"] != cls.EVENT_TYPE:
            raise ValueError(f"Tipo de evento inesperado: {payload['event_type']!r}")
        if payload["event_version"] != cls.EVENT_VERSION:
            raise ValueError(f"Versión de evento no soportada: {payload['event_version']!r}")

        data = payload["data"]
        return cls(
            event_id=UUID(payload["event_id"]),
            occurred_at=datetime.fromisoformat(payload["occurred_at"]),
            correlation_id=payload["correlation_id"],
            itinerary_id=UUID(data["itinerary_id"]),
            traveler_name=data["traveler_name"],
            traveler_email=data["traveler_email"],
            departure_airport_id=data["departure_airport_id"],
            arrival_airport_id=data["arrival_airport_id"],
            travel_date=datetime.fromisoformat(data["travel_date"]),
            duration_minutes=data["duration_minutes"],
        )

    def to_dict(self) -> dict[str, Any]:
        """Devuelve el evento con la forma exacta del contrato (listo para JSON).

        Las fechas van en ISO 8601. `occurred_at` se expresa en UTC con sufijo "Z";
        `travel_date` conserva la zona horaria original del viajero (ADR-017).
        """
        return {
            "event_id": str(self.event_id),
            "event_type": self.EVENT_TYPE,
            "event_version": self.EVENT_VERSION,
            "occurred_at": self.occurred_at.astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "producer": self.PRODUCER,
            "correlation_id": self.correlation_id,
            "data": {
                "itinerary_id": str(self.itinerary_id),
                "traveler_name": self.traveler_name,
                "traveler_email": self.traveler_email,
                "departure_airport_id": self.departure_airport_id,
                "arrival_airport_id": self.arrival_airport_id,
                "travel_date": self.travel_date.isoformat(),
                "duration_minutes": self.duration_minutes,
            },
        }
