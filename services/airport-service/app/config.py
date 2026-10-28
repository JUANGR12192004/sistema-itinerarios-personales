"""Configuración de Airport Service, leída de variables de entorno (o de un archivo .env)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Valores configurables del servicio. Cada campo se puede cambiar con una variable de entorno."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "airport-service"
    api_colombia_base_url: str = "https://api-colombia.com/api/v1"
    log_level: str = "INFO"

    # Timeout: tiempo máximo de espera de cada llamada a API Colombia (Fase 2)
    api_colombia_timeout_seconds: float = Field(default=3.0, gt=0)

    # Retry con exponential backoff: intentos totales y esperas entre ellos
    retry_max_attempts: int = Field(default=3, ge=1)
    retry_base_delay_seconds: float = Field(default=0.5, ge=0)
    retry_max_delay_seconds: float = Field(default=4.0, ge=0)

    # Circuit breaker: fallos seguidos para abrir el circuito y tiempo abierto antes de probar de nuevo
    circuit_breaker_failure_threshold: int = Field(default=3, ge=1)
    circuit_breaker_recovery_seconds: float = Field(default=30.0, gt=0)

    # Caché en Redis: datos frescos (cache_ttl) y copia de respaldo para el fallback (cache_stale_ttl)
    redis_url: str = "redis://localhost:6379/0"
    redis_timeout_seconds: float = Field(default=0.5, gt=0)
    cache_ttl_seconds: int = Field(default=600, ge=1)
    cache_stale_ttl_seconds: int = Field(default=86400, ge=1)


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración, creada una sola vez."""
    return Settings()
