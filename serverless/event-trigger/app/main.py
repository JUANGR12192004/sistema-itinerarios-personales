"""Proceso del Event Trigger (Fase 6, ADR-031).

Se ejecuta desde la carpeta serverless/event-trigger:

    python -m app.main

Cumple el papel del Event Source Mapping de AWS Lambda: lee la cola
notification.itinerary-created e invoca SendNotificationFunction con cada evento.

- Si se pierde la conexión con RabbitMQ (o RabbitMQ no ha arrancado), espera y se reconecta,
  en lugar de terminar.
- Se detiene con Ctrl+C. Si en ese momento procesaba un mensaje, el mensaje no recibió
  respuesta y RabbitMQ lo devuelve a la cola al cerrarse la conexión: no se pierde.

Este archivo es el "punto de ensamblaje": une la política (capa de aplicación) con los
adaptadores reales (pika y httpx).
"""

import logging
import time
from collections.abc import Callable

from pika.exceptions import AMQPError

from app.application.delivery_handler import DeliveryHandler, RetryPolicy
from app.config import Settings, get_settings
from app.infrastructure.lambda_invoker import LambdaFunctionInvoker
from app.infrastructure.rabbitmq.consumer import RabbitMQConsumer
from app.logging_config import configure_logging

logger = logging.getLogger(__name__)


def build_policy(settings: Settings) -> RetryPolicy:
    return RetryPolicy(
        infrastructure_attempts=settings.trigger_infrastructure_attempts,
        function_error_attempts=settings.trigger_function_error_attempts,
        backoff_seconds=settings.trigger_retry_backoff_seconds,
        max_backoff_seconds=settings.trigger_retry_max_backoff_seconds,
        requeue_delay_seconds=settings.trigger_requeue_delay_seconds,
    )


def build_consumer(settings: Settings, invoker: LambdaFunctionInvoker) -> RabbitMQConsumer:
    """Ensambla el consumidor: la política usa el invocador HTTP y la espera de la conexión."""
    policy = build_policy(settings)
    return RabbitMQConsumer(
        url=settings.rabbitmq_url,
        timeout_seconds=settings.rabbitmq_timeout_seconds,
        handler_factory=lambda sleep: DeliveryHandler(invoker, policy, sleep),
    )


def run_with_reconnection(
    run_consumer: Callable[[], object],
    reconnect_delay_seconds: float,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Ejecuta el consumidor y lo vuelve a conectar si se pierde la conexión, hasta Ctrl+C."""
    while True:
        try:
            run_consumer()
            logger.warning("El consumo terminó (RabbitMQ canceló el consumidor); se reconecta")
        except KeyboardInterrupt:
            logger.info("Event Trigger detenido (Ctrl+C)")
            return
        except (AMQPError, OSError) as exc:
            logger.warning(
                "Sin conexión con RabbitMQ (%s). Reintento en %.1f s",
                type(exc).__name__,
                reconnect_delay_seconds,
            )
        try:
            sleep(reconnect_delay_seconds)
        except KeyboardInterrupt:
            logger.info("Event Trigger detenido (Ctrl+C)")
            return


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.service_name)
    # pika registra cada intento de conexión fallido con su traza; el trigger ya informa
    # el error en una línea y se reconecta
    logging.getLogger("pika").setLevel(logging.CRITICAL)
    # httpx registra cada solicitud en INFO; el trigger ya informa el resultado de cada invocación
    logging.getLogger("httpx").setLevel(logging.WARNING)

    invoker = LambdaFunctionInvoker(settings.function_invoke_url, settings.function_timeout_seconds)
    consumer = build_consumer(settings, invoker)
    logger.info("Event Trigger iniciado; invoca la función en %s", settings.function_invoke_url)
    try:
        run_with_reconnection(consumer.run, settings.rabbitmq_reconnect_delay_seconds)
    finally:
        invoker.close()


if __name__ == "__main__":
    main()
