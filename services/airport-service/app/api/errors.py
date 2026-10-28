"""Manejador único de errores: traduce excepciones a HTTP con el formato de la sección 10.2.

| Excepción                        | HTTP | code                         |
|----------------------------------|------|------------------------------|
| AirportNotFoundError             | 404  | AIRPORT_NOT_FOUND            |
| RequestValidationError (FastAPI) | 422  | VALIDATION_ERROR             |
| AirportProviderResponseError     | 502  | AIRPORT_PROVIDER_BAD_RESPONSE|
| AirportProviderUnavailableError  | 503  | AIRPORT_PROVIDER_UNAVAILABLE |
| AirportProviderTimeoutError      | 504  | AIRPORT_PROVIDER_TIMEOUT     |
| Ruta inexistente u otro error HTTP | 404/405/... | ROUTE_NOT_FOUND, METHOD_NOT_ALLOWED, HTTP_ERROR |
| Cualquier otra excepción         | 500  | INTERNAL_ERROR               |
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.correlation import CORRELATION_ID_HEADER, get_correlation_id
from app.api.schemas import ErrorBody, ErrorResponse
from app.application.exceptions import (
    AirportProviderResponseError,
    AirportProviderTimeoutError,
    AirportProviderUnavailableError,
)
from app.domain import AirportNotFoundError

logger = logging.getLogger(__name__)

_HTTP_ERROR_CODES = {
    status.HTTP_404_NOT_FOUND: "ROUTE_NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
}


def error_response(
    request: Request, status_code: int, code: str, message: str, details: dict[str, Any] | None = None
) -> JSONResponse:
    """Construye una respuesta de error con el formato único."""
    correlation_id = get_correlation_id(request)
    body = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details or {}),
        correlation_id=correlation_id,
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(),
        headers={CORRELATION_ID_HEADER: correlation_id},
    )


async def _airport_not_found(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, AirportNotFoundError)
    return error_response(
        request, status.HTTP_404_NOT_FOUND, "AIRPORT_NOT_FOUND", str(error), {"airport_id": error.airport_id}
    )


async def _validation_error(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, RequestValidationError)
    errors = [
        {"field": ".".join(str(part) for part in item["loc"][1:]) or str(item["loc"][0]), "message": item["msg"]}
        for item in error.errors()
    ]
    return error_response(
        request,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "VALIDATION_ERROR",
        "Los datos de la solicitud no son válidos",
        {"errors": errors},
    )


async def _provider_bad_response(request: Request, error: Exception) -> JSONResponse:
    logger.warning("Respuesta inválida del proveedor de aeropuertos: %s", error)
    return error_response(
        request,
        status.HTTP_502_BAD_GATEWAY,
        "AIRPORT_PROVIDER_BAD_RESPONSE",
        "El proveedor de aeropuertos respondió algo inesperado",
    )


async def _provider_unavailable(request: Request, error: Exception) -> JSONResponse:
    logger.warning("Proveedor de aeropuertos no disponible: %s", error)
    return error_response(
        request,
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "AIRPORT_PROVIDER_UNAVAILABLE",
        "El proveedor de aeropuertos no está disponible, intente más tarde",
    )


async def _provider_timeout(request: Request, error: Exception) -> JSONResponse:
    logger.warning("El proveedor de aeropuertos no respondió a tiempo: %s", error)
    return error_response(
        request,
        status.HTTP_504_GATEWAY_TIMEOUT,
        "AIRPORT_PROVIDER_TIMEOUT",
        "El proveedor de aeropuertos no respondió a tiempo, intente más tarde",
    )


async def _http_error(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, StarletteHTTPException)
    code = _HTTP_ERROR_CODES.get(error.status_code, "HTTP_ERROR")
    return error_response(request, error.status_code, code, str(error.detail))


async def _unexpected_error(request: Request, error: Exception) -> JSONResponse:
    logger.exception("Error inesperado procesando %s %s", request.method, request.url.path)
    return error_response(
        request, status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "Ocurrió un error interno inesperado"
    )


def register_error_handlers(app: FastAPI) -> None:
    """Registra todos los manejadores en la aplicación (un único punto de traducción a HTTP)."""
    app.add_exception_handler(AirportNotFoundError, _airport_not_found)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(AirportProviderResponseError, _provider_bad_response)
    app.add_exception_handler(AirportProviderUnavailableError, _provider_unavailable)
    # AirportProviderTimeoutError hereda de AirportProviderUnavailableError, pero FastAPI usa el
    # manejador de la clase más específica: un timeout responde 504, no 503.
    app.add_exception_handler(AirportProviderTimeoutError, _provider_timeout)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(Exception, _unexpected_error)
