"""Configuración de Itinerary Service, leída de variables de entorno (o de un archivo .env)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Valores configurables del servicio. Cada campo se puede cambiar con una variable de entorno."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "itinerary-service"
    log_level: str = "INFO"

    # Cadena de conexión a PostgreSQL (psycopg 3, modo síncrono)
    database_url: str = Field(
        default="postgresql+psycopg://itinerary:itinerary@localhost:5433/itinerary_db"
    )

    # URL de Airport Service y timeout de sus llamadas HTTP
    airport_service_url: str = Field(default="http://localhost:8001")
    airport_service_timeout_seconds: float = Field(default=5.0, gt=0)


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración, creada una sola vez."""
    return Settings()
