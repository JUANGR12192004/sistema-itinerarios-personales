"""Configuración de SendNotificationFunction, leída de variables de entorno (o de un archivo .env).

Dentro de la imagen de Lambda no hay archivo .env: las variables se pasan al contenedor
(`docker run -e ...`; en AWS, en la configuración de la función).
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Valores configurables de la función. Cada campo se puede cambiar con una variable de entorno."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    function_name: str = "send-notification-function"
    log_level: str = "INFO"

    # Cadena de conexión al PostgreSQL de notificaciones (ADR-029).
    # Sin valor por defecto para no dejar credenciales en el código (ver .env.example).
    database_url: str
    # Tiempo máximo para abrir una conexión (segundos enteros; psycopg trata los menores que 2 como 2).
    # Debe ser bastante menor que el timeout de la función (10 s) para responder TransientError a tiempo.
    database_connect_timeout_seconds: int = Field(default=3, ge=2)


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración, creada una sola vez por contenedor."""
    return Settings()
