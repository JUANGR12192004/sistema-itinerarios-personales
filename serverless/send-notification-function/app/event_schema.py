"""Esquema Pydantic del contrato ItineraryCreatedEvent v1 (ADR-020), del lado del consumidor.

Cumple el papel de `api/schemas.py` en los servicios: valida la entrada externa y la
convierte en el objeto de la capa de aplicación (ItineraryCreatedEvent).

Tolerant Reader: los campos que no se conocen se ignoran (`extra="ignore"`). Un campo
nuevo y compatible agregado por el productor no rompe al consumidor; un cambio
incompatible llegaría con otra `event_version` y se rechaza.
"""

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from app.application.events import ItineraryCreatedEvent
from app.application.exceptions import InvalidEventError

EVENT_TYPE = "itinerary.created"
SUPPORTED_EVENT_VERSION = 1
MAX_REPORTED_ERRORS = 5

NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ItineraryCreatedDataSchema(BaseModel):
    """Campo `data` del evento."""

    model_config = ConfigDict(extra="ignore")

    itinerary_id: UUID
    traveler_name: NonBlankStr
    traveler_email: str | None = None
    departure_airport_id: int = Field(ge=1)
    arrival_airport_id: int = Field(ge=1)
    travel_date: AwareDatetime
    duration_minutes: int = Field(ge=1)


class ItineraryCreatedEventSchema(BaseModel):
    """Evento completo, versión 1."""

    model_config = ConfigDict(extra="ignore")

    event_id: UUID
    event_type: Literal["itinerary.created"]
    event_version: Literal[1]
    occurred_at: AwareDatetime
    producer: str
    correlation_id: str
    data: ItineraryCreatedDataSchema


def parse_event(raw: Any) -> ItineraryCreatedEvent:
    """Valida el evento recibido por el handler y lo convierte al objeto de aplicación.

    Raises:
        InvalidEventError: el evento no cumple el contrato v1 (fallo permanente).
    """
    if not isinstance(raw, dict):
        raise InvalidEventError(
            f"El evento debe ser un objeto JSON; se recibió {type(raw).__name__}"
        )

    event_id = _try_read_event_id(raw)

    # Se revisan primero el tipo y la versión para dar un motivo claro
    event_type = raw.get("event_type")
    if event_type != EVENT_TYPE:
        raise InvalidEventError(
            f"event_type desconocido: {event_type!r} (se esperaba {EVENT_TYPE!r})", event_id
        )
    event_version = raw.get("event_version")
    if event_version != SUPPORTED_EVENT_VERSION:
        raise InvalidEventError(
            f"event_version no soportada: {event_version!r} "
            f"(esta función procesa la versión {SUPPORTED_EVENT_VERSION})",
            event_id,
        )

    try:
        schema = ItineraryCreatedEventSchema.model_validate(raw)
    except ValidationError as error:
        raise InvalidEventError(_describe_errors(error), event_id) from error

    return ItineraryCreatedEvent(
        event_id=schema.event_id,
        occurred_at=schema.occurred_at,
        correlation_id=schema.correlation_id,
        itinerary_id=schema.data.itinerary_id,
        traveler_name=schema.data.traveler_name,
        traveler_email=schema.data.traveler_email,
        departure_airport_id=schema.data.departure_airport_id,
        arrival_airport_id=schema.data.arrival_airport_id,
        travel_date=schema.data.travel_date,
        duration_minutes=schema.data.duration_minutes,
    )


def _try_read_event_id(raw: dict[str, Any]) -> UUID | None:
    """Lee el event_id aunque el resto del evento sea inválido, para identificarlo en los logs."""
    try:
        return UUID(str(raw.get("event_id")))
    except ValueError:
        return None


def _describe_errors(error: ValidationError) -> str:
    """Resume los errores de Pydantic en una línea: 'campo: problema; campo: problema'."""
    details = [
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
        for item in error.errors()[:MAX_REPORTED_ERRORS]
    ]
    return "El evento no cumple el contrato v1: " + "; ".join(details)
