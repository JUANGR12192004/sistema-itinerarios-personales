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
    """Crea y cachea el engine de SQLAlchemy usando DATABASE_URL."""
    return create_engine(get_settings().database_url)


def get_session_factory() -> sessionmaker[Session]:
    """Devuelve la factoría de sesiones sincrónicas."""
    return sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
