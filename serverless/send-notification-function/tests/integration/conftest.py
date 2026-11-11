"""Fixtures para las pruebas de integración con el PostgreSQL de notificaciones (puerto 5434).

pg_engine       — engine de la sesión de pytest; None si PostgreSQL no está disponible.
session_factory — factoría de sesiones con la tabla notification_history vacía.

Si PostgreSQL no responde, las pruebas quedan SKIPPED (no FAILED). Requieren la
migración aplicada (`alembic upgrade head`).
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

# Espera máxima (segundos) para comprobar si PostgreSQL está disponible. Sin este límite,
# psycopg espera hasta 130 s por cada dirección de localhost (::1 y 127.0.0.1 en Windows).
CONNECT_TIMEOUT_SECONDS = 2


@pytest.fixture(scope="session")
def pg_engine():
    try:
        engine = create_engine(
            get_settings().database_url,
            connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
        )
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        yield None
        return
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(pg_engine):
    """Factoría de sesiones; vacía notification_history antes y después de cada prueba."""
    if pg_engine is None:
        pytest.skip("PostgreSQL de notificaciones no disponible — omitiendo prueba de integración")

    factory = sessionmaker(bind=pg_engine, autocommit=False, autoflush=False)
    _clean(factory)
    yield factory
    _clean(factory)


def count_rows(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        return session.execute(text("SELECT COUNT(*) FROM notification_history")).scalar_one()


def _clean(factory: sessionmaker[Session]) -> None:
    with factory() as session:
        session.execute(text("DELETE FROM notification_history"))
        session.commit()
