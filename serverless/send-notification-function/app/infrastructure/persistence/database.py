"""Engine y factoría de sesiones de SQLAlchemy (modo síncrono).

El engine se crea la primera vez que se usa y se conserva mientras el contenedor de la
función siga "caliente" (ADR-028): así las invocaciones siguientes reutilizan la conexión
en lugar de abrir una nueva. Es lo único que la función conserva entre invocaciones;
no guarda datos de negocio en memoria.
"""

from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Crea y cachea el engine usando DATABASE_URL.

    - connect_timeout: limita la espera al abrir una conexión, para que un PostgreSQL
      apagado se informe como TransientError antes del timeout de la función.
    - pool_pre_ping: comprueba la conexión guardada antes de usarla; si PostgreSQL se
      reinició mientras el contenedor estaba caliente, abre una nueva en lugar de fallar.
    - hide_parameters: los mensajes de error de SQLAlchemy no incluyen los valores del SQL
      (el correo y el nombre del viajero). Esos mensajes llegan al log de la función.
    """
    settings = get_settings()
    return create_engine(
        settings.database_url,
        connect_args={"connect_timeout": settings.database_connect_timeout_seconds},
        pool_pre_ping=True,
        hide_parameters=True,
    )


def get_session_factory() -> sessionmaker[Session]:
    """Devuelve la factoría de sesiones (una sesión por invocación)."""
    return sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
