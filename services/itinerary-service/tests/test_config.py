"""Pruebas de la configuración del servicio (app/config.py).

Se usa _env_file=None para que el archivo .env local no influya en el resultado.
"""

import pytest
from pydantic import ValidationError

from app.config import Settings

DATABASE_URL = "postgresql+psycopg://localhost:5433/itinerary_db"


def test_database_url_es_obligatoria(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sin DATABASE_URL la configuración falla: el servicio no trae credenciales por defecto."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)

    assert error.value.errors()[0]["loc"] == ("database_url",)
    assert error.value.errors()[0]["type"] == "missing"


def test_connect_timeout_por_defecto_es_cinco_segundos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_CONNECT_TIMEOUT_SECONDS", raising=False)

    settings = Settings(_env_file=None, database_url=DATABASE_URL)

    assert settings.database_connect_timeout_seconds == 5


def test_connect_timeout_se_lee_de_la_variable_de_entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_CONNECT_TIMEOUT_SECONDS", "3")

    settings = Settings(_env_file=None, database_url=DATABASE_URL)

    assert settings.database_connect_timeout_seconds == 3


@pytest.mark.parametrize("value", ["0", "1", "-5"])
def test_connect_timeout_menor_que_dos_se_rechaza(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """psycopg trata los valores menores que 2 como 2 (y 0 como 'sin límite'): se rechazan."""
    monkeypatch.setenv("DATABASE_CONNECT_TIMEOUT_SECONDS", value)

    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url=DATABASE_URL)
