"""Engine y factoría de sesiones de SQLAlchemy (modo síncrono).

El engine se crea una sola vez (lru_cache). Las sesiones se crean por solicitud
en el dependency de FastAPI (entrega 3D); aquí solo se define la factoría.
"""

from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Crea y cachea el engine de SQLAlchemy usando DATABASE_URL.

    - connect_timeout: limita la espera al abrir una conexión. Sin él, psycopg espera
      hasta 130 s por cada dirección del host (en Windows, localhost tiene dos: ::1 y 127.0.0.1).
    - hide_parameters: los mensajes de error de SQLAlchemy no incluyen los valores del SQL
      (el nombre y el correo del viajero). Esos mensajes llegan al log del servicio y del relay.
    """
    settings = get_settings()
    return create_engine(
        settings.database_url,
        connect_args={"connect_timeout": settings.database_connect_timeout_seconds},
        hide_parameters=True,
    )


def get_session_factory() -> sessionmaker[Session]:
    """Devuelve la factoría de sesiones sincrónicas."""
    return sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
