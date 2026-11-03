"""Manejador único de errores de Itinerary Service.

Convierte las excepciones del dominio y de la aplicación al formato HTTP acordado:
  {"error": {"code": "...", "message": "...", "details": ...}, "correlation_id": "..."}

AirportServiceTimeoutError se registra antes que AirportServiceUnavailableError porque
es su subclase; Starlette resuelve por MRO, pero el orden explícito ayuda a la claridad.
"""

import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.application.exceptions import (
    AirportServiceTimeoutError,
    AirportServiceUnavailableError,
    ArrivalAirportNotFoundError,
    DepartureAirportNotFoundError,
    ItineraryNotFoundError,
)
from app.domain.exceptions import InvalidItineraryError

logger = logging.getLogger(__name__)

_HTTP_ERROR_CODES = {
    404: "ROUTE_NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
}


def _cid(request: Request) -> str:
    return request.headers.get("X-Correlation-ID", str(uuid4()))


def _body(code: str, message: str, details: dict | None, correlation_id: str) -> dict:
    return {
        "error": {"code": code, "message": message, "details": details or {}},
        "correlation_id": correlation_id,
    }


def add_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError):
        cid = _cid(request)
        return JSONResponse(
            status_code=422,
            content=_body("VALIDATION_ERROR", "Los datos de la solicitud no son válidos.", {"errors": exc.errors()}, cid),
            headers={"X-Correlation-ID": cid},
        )

    @app.exception_handler(InvalidItineraryError)
    async def handle_invalid_itinerary(request: Request, exc: InvalidItineraryError):
        cid = _cid(request)
        return JSONResponse(
            status_code=422,
            content=_body("INVALID_ITINERARY", str(exc), None, cid),
            headers={"X-Correlation-ID": cid},
        )

    @app.exception_handler(ItineraryNotFoundError)
    async def handle_itinerary_not_found(request: Request, exc: ItineraryNotFoundError):
        cid = _cid(request)
        return JSONResponse(
            status_code=404,
            content=_body("ITINERARY_NOT_FOUND", str(exc), {"itinerary_id": str(exc.itinerary_id)}, cid),
            headers={"X-Correlation-ID": cid},
        )

    @app.exception_handler(DepartureAirportNotFoundError)
    async def handle_departure_not_found(request: Request, exc: DepartureAirportNotFoundError):
        cid = _cid(request)
        return JSONResponse(
            status_code=422,
            content=_body(
                "AIRPORT_NOT_FOUND",
                f"El aeropuerto de salida con id {exc.airport_id} no existe.",
                {"field": "departure_airport_id"},
                cid,
            ),
            headers={"X-Correlation-ID": cid},
        )

    @app.exception_handler(ArrivalAirportNotFoundError)
    async def handle_arrival_not_found(request: Request, exc: ArrivalAirportNotFoundError):
        cid = _cid(request)
        return JSONResponse(
            status_code=422,
            content=_body(
                "AIRPORT_NOT_FOUND",
                f"El aeropuerto de llegada con id {exc.airport_id} no existe.",
                {"field": "arrival_airport_id"},
                cid,
            ),
            headers={"X-Correlation-ID": cid},
        )

    @app.exception_handler(AirportServiceTimeoutError)
    async def handle_airport_timeout(request: Request, exc: AirportServiceTimeoutError):
        cid = _cid(request)
        logger.error("Airport Service timeout: %s", exc)
        return JSONResponse(
            status_code=504,
            content=_body("AIRPORT_SERVICE_TIMEOUT", "Airport Service no respondió a tiempo.", None, cid),
            headers={"X-Correlation-ID": cid},
        )

    @app.exception_handler(AirportServiceUnavailableError)
    async def handle_airport_unavailable(request: Request, exc: AirportServiceUnavailableError):
        cid = _cid(request)
        logger.error("Airport Service no disponible: %s", exc)
        return JSONResponse(
            status_code=503,
            content=_body("AIRPORT_SERVICE_UNAVAILABLE", "Airport Service no está disponible.", None, cid),
            headers={"X-Correlation-ID": cid},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException):
        # Captura rutas inexistentes (404) y métodos no permitidos (405) que lanza Starlette
        # antes de que lleguen a nuestras rutas. Sin este manejador responde {"detail":"..."}.
        cid = _cid(request)
        code = _HTTP_ERROR_CODES.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(code, str(exc.detail), None, cid),
            headers={"X-Correlation-ID": cid},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        cid = _cid(request)
        logger.exception("Error inesperado procesando %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=_body("INTERNAL_ERROR", "Ocurrió un error interno inesperado.", None, cid),
            headers={"X-Correlation-ID": cid},
        )
