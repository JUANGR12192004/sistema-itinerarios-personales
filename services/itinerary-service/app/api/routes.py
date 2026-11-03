"""Rutas REST de Itinerary Service (CRUD completo)."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_airport_catalog,
    get_event_publisher,
    get_itinerary_repository,
)
from app.api.schemas import CreateItineraryRequest, ItineraryResponse, UpdateItineraryRequest
from app.application.ports import AirportCatalog, EventPublisher, ItineraryRepository
from app.application.use_cases import (
    CreateItineraryCommand,
    CreateItineraryUseCase,
    DeleteItineraryUseCase,
    GetItineraryUseCase,
    ListItinerariesUseCase,
    UpdateItineraryCommand,
    UpdateItineraryUseCase,
)

router = APIRouter(prefix="/itineraries", tags=["Itinerarios"])


@router.post("", status_code=201, response_model=ItineraryResponse)
def create_itinerary(
    body: CreateItineraryRequest,
    repo: ItineraryRepository = Depends(get_itinerary_repository),
    catalog: AirportCatalog = Depends(get_airport_catalog),
    publisher: EventPublisher = Depends(get_event_publisher),
) -> ItineraryResponse:
    result = CreateItineraryUseCase(repo, catalog, publisher).execute(
        CreateItineraryCommand(
            traveler_name=body.traveler_name,
            traveler_email=body.traveler_email,
            departure_airport_id=body.departure_airport_id,
            arrival_airport_id=body.arrival_airport_id,
            travel_date=body.travel_date,
            duration_minutes=body.duration_minutes,
        )
    )
    return ItineraryResponse.model_validate(result)


@router.get("")
def list_itineraries(
    repo: ItineraryRepository = Depends(get_itinerary_repository),
) -> list[ItineraryResponse]:
    return [
        ItineraryResponse.model_validate(it)
        for it in ListItinerariesUseCase(repo).execute()
    ]


@router.get("/{itinerary_id}")
def get_itinerary(
    itinerary_id: UUID,
    repo: ItineraryRepository = Depends(get_itinerary_repository),
) -> ItineraryResponse:
    return ItineraryResponse.model_validate(GetItineraryUseCase(repo).execute(itinerary_id))


@router.put("/{itinerary_id}", response_model=ItineraryResponse)
def update_itinerary(
    itinerary_id: UUID,
    body: UpdateItineraryRequest,
    repo: ItineraryRepository = Depends(get_itinerary_repository),
    catalog: AirportCatalog = Depends(get_airport_catalog),
) -> ItineraryResponse:
    result = UpdateItineraryUseCase(repo, catalog).execute(
        itinerary_id,
        UpdateItineraryCommand(
            traveler_name=body.traveler_name,
            traveler_email=body.traveler_email,
            departure_airport_id=body.departure_airport_id,
            arrival_airport_id=body.arrival_airport_id,
            travel_date=body.travel_date,
            duration_minutes=body.duration_minutes,
        ),
    )
    return ItineraryResponse.model_validate(result)


@router.delete("/{itinerary_id}", status_code=204)
def delete_itinerary(
    itinerary_id: UUID,
    repo: ItineraryRepository = Depends(get_itinerary_repository),
) -> None:
    DeleteItineraryUseCase(repo).execute(itinerary_id)
