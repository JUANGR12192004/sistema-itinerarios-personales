"""Configuración del Event Trigger, leída de variables de entorno (o de un archivo .env)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Valores configurables del trigger. Cada campo se puede cambiar con una variable de entorno."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "event-trigger"
    log_level: str = "INFO"

    # RabbitMQ. Sin usuario en la URL, pika usa guest/guest (usuario por defecto de la imagen local).
    rabbitmq_url: str = Field(default="amqp://localhost:5672/%2F")
    # Tiempo máximo para conectar con RabbitMQ (segundos)
    rabbitmq_timeout_seconds: float = Field(default=3.0, gt=0)
    # Pausa antes de reconectar si se pierde la conexión con RabbitMQ (segundos)
    rabbitmq_reconnect_delay_seconds: float = Field(default=5.0, ge=0)

    # Puerto del servidor HTTP de métricas (Fase 9C, ADR-038)
    metrics_port: int = Field(default=9102, gt=0)

    # API de invocación de SendNotificationFunction (Runtime Interface Emulator, ADR-008)
    function_invoke_url: str = Field(
        default="http://localhost:9000/2015-03-31/functions/function/invocations"
    )
    # Tiempo máximo de una invocación; mayor que el timeout de la función (10 s)
    function_timeout_seconds: float = Field(default=15.0, gt=0)

    # Política de reintentos (ADR-031)
    trigger_infrastructure_attempts: int = Field(default=3, ge=1)
    trigger_function_error_attempts: int = Field(default=3, ge=1)
    trigger_retry_backoff_seconds: float = Field(default=1.0, ge=0)
    trigger_retry_max_backoff_seconds: float = Field(default=8.0, ge=0)
    trigger_requeue_delay_seconds: float = Field(default=10.0, ge=0)


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración, creada una sola vez."""
    return Settings()
