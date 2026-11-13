"""Correlation ID: un identificador por solicitud para relacionar logs y errores.

Si el cliente envía el header X-Correlation-ID se reutiliza; si no, se genera uno.
Siempre se devuelve en el header de la respuesta y en el cuerpo de los errores.
Desde la Fase 9A también se guarda en un ContextVar para que el logging filter
lo incluya automáticamente en cada línea de log de esa solicitud.
"""

import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.logging_config import set_correlation_id

CORRELATION_ID_HEADER = "X-Correlation-ID"
MAX_CORRELATION_ID_LENGTH = 128


async def correlation_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    received = request.headers.get(CORRELATION_ID_HEADER, "").strip()
    correlation_id = received[:MAX_CORRELATION_ID_LENGTH] or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    set_correlation_id(correlation_id)

    response = await call_next(request)
    response.headers[CORRELATION_ID_HEADER] = correlation_id
    return response


def get_correlation_id(request: Request) -> str:
    """Devuelve el correlation ID de la solicitud (o genera uno si el middleware no corrió)."""
    return getattr(request.state, "correlation_id", None) or str(uuid.uuid4())
