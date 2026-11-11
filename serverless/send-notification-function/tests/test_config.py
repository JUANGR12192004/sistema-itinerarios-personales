"""Pruebas de la configuración de la función."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_valores_por_defecto():
    settings = Settings(database_url="postgresql+psycopg://localhost:5434/notification_db")

    assert settings.function_name == "send-notification-function"
    assert settings.database_connect_timeout_seconds == 3
    assert settings.log_level == "INFO"


def test_el_timeout_de_conexion_no_puede_ser_menor_que_2():
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+psycopg://localhost:5434/notification_db",
            database_connect_timeout_seconds=1,
        )
