"""Fixtures de infraestructura para las pruebas de integración del repositorio.

pg_engine  — engine de sesión; yield None si PostgreSQL no está disponible.
db_session — sesión por prueba con limpieza automática de la tabla itineraries.
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import get_settings

# Espera máxima (segundos) para comprobar si PostgreSQL está disponible. Sin este límite,
# psycopg espera hasta 130 s por cada dirección de localhost (::1 y 127.0.0.1 en Windows).
CONNECT_TIMEOUT_SECONDS = 2


@pytest.fixture(scope="session")
def pg_engine():
    """Crea el engine una sola vez por sesión de pytest.

    Si PostgreSQL no responde, devuelve None; db_session se encarga de saltar
    cada prueba individualmente para que aparezcan como SKIPPED en el reporte.
    """
    settings = get_settings()
    try:
        engine = create_engine(
            settings.database_url,
            connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
        )
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

    Limpieza: elimina todos los registros de itineraries y outbox_events antes y
    después de cada prueba para garantizar aislamiento entre tests. Requiere las
    migraciones aplicadas (`alembic upgrade head`).
    """
    if pg_engine is None:
        pytest.skip("PostgreSQL no disponible — omitiendo prueba de integración")

    session = Session(pg_engine)
    _clean_tables(session)

    yield session

    session.rollback()  # por si la prueba dejó una transacción a medias
    _clean_tables(session)
    session.close()


def _clean_tables(session: Session) -> None:
    session.execute(text("DELETE FROM outbox_events"))
    session.execute(text("DELETE FROM itineraries"))
    session.commit()
