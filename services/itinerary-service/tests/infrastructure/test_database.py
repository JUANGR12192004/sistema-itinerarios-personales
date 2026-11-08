"""Pruebas del engine de SQLAlchemy (app/infrastructure/persistence/database.py).

No se conecta a PostgreSQL: se reemplaza create_engine para ver con qué argumentos se llama.
"""

from collections.abc import Iterator
from typing import Any

import pytest

from app.config import Settings
from app.infrastructure.persistence import database

DATABASE_URL = "postgresql+psycopg://localhost:5433/itinerary_db"


@pytest.fixture(autouse=True)
def clear_engine_cache() -> Iterator[None]:
    """get_engine está cacheado: se limpia antes y después para no afectar a otras pruebas."""
    database.get_engine.cache_clear()
    yield
    database.get_engine.cache_clear()


def test_engine_usa_el_connect_timeout_configurado(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        _env_file=None, database_url=DATABASE_URL, database_connect_timeout_seconds=7
    )
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_create_engine(url: str, **kwargs: Any) -> object:
        calls.append((url, kwargs))
        return object()

    monkeypatch.setattr(database, "get_settings", lambda: settings)
    monkeypatch.setattr(database, "create_engine", fake_create_engine)

    database.get_engine()

    assert calls == [(DATABASE_URL, {"connect_args": {"connect_timeout": 7}})]
