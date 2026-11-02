"""Fixtures de infraestructura para las pruebas de integración del repositorio.

pg_engine  — engine de sesión; yield None si PostgreSQL no está disponible.
db_session — sesión por prueba con limpieza automática de la tabla itineraries.
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import get_settings


@pytest.fixture(scope="session")
def pg_engine():
    """Crea el engine una sola vez por sesión de pytest.

    Si PostgreSQL no responde, devuelve None; db_session se encarga de saltar
    cada prueba individualmente para que aparezcan como SKIPPED en el reporte.
    """
    settings = get_settings()
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        yield engine
        engine.dispose()
    except Exception:
        yield None


@pytest.fixture
def db_session(pg_engine):
    """Sesión limpia para cada prueba.

    Si pg_engine es None (PostgreSQL no disponible) la prueba se marca como
    SKIPPED, no como FAILED, para que el CI siga en verde sin base de datos.

    Limpieza: elimina todos los registros de itineraries antes y después de
    cada prueba para garantizar aislamiento entre tests.
    """
    if pg_engine is None:
        pytest.skip("PostgreSQL no disponible — omitiendo prueba de integración")

    session = Session(pg_engine)
    session.execute(text("DELETE FROM itineraries"))
    session.commit()

    yield session

    session.execute(text("DELETE FROM itineraries"))
    session.commit()
    session.close()
