"""Traducción de los errores de conexión de SQLAlchemy a TransientError (ADR-028).

Solo los errores de INFRAESTRUCTURA se convierten: PostgreSQL apagado, timeout de conexión
o conexión cortada. Son temporales: el mismo evento funcionará cuando vuelva la base de datos.

Cualquier otro error (por ejemplo, "la tabla no existe" porque falta aplicar la migración,
o un error de programación) se deja pasar tal cual: no se arregla esperando.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.exc import DisconnectionError, InterfaceError, OperationalError

from app.application.exceptions import TransientError

# OperationalError: no se pudo conectar, timeout o el servidor cerró la conexión.
# InterfaceError: la conexión del driver quedó inutilizable.
# DisconnectionError: el pool detectó una conexión cortada.
DATABASE_UNAVAILABLE_ERRORS = (OperationalError, InterfaceError, DisconnectionError)


@contextmanager
def translate_database_errors() -> Iterator[None]:
    """Envuelve una operación con la base de datos y convierte los fallos de conexión."""
    try:
        yield
    except DATABASE_UNAVAILABLE_ERRORS as exc:
        raise TransientError(
            "La base de datos del historial de notificaciones no está disponible"
        ) from exc
