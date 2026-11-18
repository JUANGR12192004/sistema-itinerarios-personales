"""Fixtures para las pruebas de integración con el PostgreSQL de notificaciones (puerto 5434).

pg_engine       — engine de la base de PRUEBAS (notification_db_test, creada y migrada al empezar);
                  None si PostgreSQL no está disponible.
session_factory — factoría de sesiones con la tabla notification_history vacía.

Si PostgreSQL no responde, las pruebas quedan SKIPPED (no FAILED).

AISLAMIENTO (Fase 11): las pruebas NO usan la base real notification_db, sino notification_db_test
en el mismo servidor (ver tests/integration/database_setup.py): vaciar notification_history no borra
el historial de una demostración.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.infrastructure.persistence.database import get_engine
from tests.integration.database_setup import prepare_test_database


@pytest.fixture(scope="session")
def pg_engine():
    engine = prepare_test_database(get_settings().database_url)
    yield engine
    if engine is not None:
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


@pytest.fixture
def handler_database(pg_engine, monkeypatch: pytest.MonkeyPatch):
    """Hace que el handler real (que arma su propio engine con DATABASE_URL) use la base de pruebas.

    get_settings y get_engine están cacheados (lru_cache): se vacían al empezar, para que lean la
    URL de pruebas, y al terminar, para que nada quede apuntando a la base de pruebas.
    """
    if pg_engine is None:
        pytest.skip("PostgreSQL de notificaciones no disponible — omitiendo prueba de integración")
    monkeypatch.setenv("DATABASE_URL", pg_engine.url.render_as_string(hide_password=False))
    get_settings.cache_clear()
    get_engine.cache_clear()
    yield
    get_engine().dispose()
    get_engine.cache_clear()
    get_settings.cache_clear()


def count_rows(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        return session.execute(text("SELECT COUNT(*) FROM notification_history")).scalar_one()


def _clean(factory: sessionmaker[Session]) -> None:
    with factory() as session:
        session.execute(text("DELETE FROM notification_history"))
        session.commit()
