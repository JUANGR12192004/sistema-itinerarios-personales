"""Configuración de Airport Service, leída de variables de entorno (o de un archivo .env)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Valores configurables del servicio. Cada campo se puede cambiar con una variable de entorno."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "airport-service"
    api_colombia_base_url: str = "https://api-colombia.com/api/v1"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración, creada una sola vez."""
    return Settings()
