"""Configuración de Itinerary Service, leída de variables de entorno (o de un archivo .env)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Valores configurables del servicio. Cada campo se puede cambiar con una variable de entorno."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "itinerary-service"
    log_level: str = "INFO"

    # Cadena de conexión a PostgreSQL (psycopg 3, modo síncrono).
    # Configurar con la variable de entorno DATABASE_URL o en el archivo .env (ver .env.example).
    # No tiene valor por defecto para no dejar credenciales en el código.
    database_url: str
    # Tiempo máximo para abrir una conexión a PostgreSQL (segundos enteros, como espera libpq).
    # psycopg trata los valores menores que 2 como 2, por eso el mínimo es 2.
    database_connect_timeout_seconds: int = Field(default=5, ge=2)

    # URL de Airport Service y timeout de sus llamadas HTTP
    airport_service_url: str = Field(default="http://localhost:8001")
    airport_service_timeout_seconds: float = Field(default=5.0, gt=0)

    # Conexión a RabbitMQ (Fase 4). Sin usuario en la URL, pika usa guest/guest,
    # el usuario por defecto de la imagen local de RabbitMQ. Ver .env.example.
    rabbitmq_url: str = Field(default="amqp://localhost:5672/%2F")
    # Tiempo máximo para conectar y para cada operación con RabbitMQ (segundos)
    rabbitmq_timeout_seconds: float = Field(default=3.0, gt=0)

    # Outbox Relay (Fase 5, ADR-025): cada cuántos segundos revisa la outbox
    # y cuántos eventos pendientes toma como máximo en cada ciclo.
    outbox_relay_poll_interval_seconds: float = Field(default=2.0, gt=0)
    outbox_relay_batch_size: int = Field(default=10, ge=1)

    # Host y puerto de uvicorn. En Docker (Fase 10) usar HOST=0.0.0.0.
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8002, gt=0)

    # Puerto del servidor HTTP de métricas del Outbox Relay (Fase 9C, ADR-038).
    # Proceso separado de la API: tiene su propio registro de Prometheus.
    outbox_relay_metrics_port: int = Field(default=9101, gt=0)


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración, creada una sola vez."""
    return Settings()
