"""Comando para reprocesar la DLQ (ADR-031).

Devuelve mensajes de notification.itinerary-created.dlq a notification.itinerary-created,
para que el Event Trigger los procese otra vez. Usarlo DESPUÉS de corregir la causa del
fallo (por ejemplo, aplicar la migración del historial o corregir la imagen de la función).

Desde la carpeta serverless/event-trigger, con el entorno virtual activado:

    python -m app.replay_dlq            → mueve UN mensaje (el más antiguo)
    python -m app.replay_dlq --all      → mueve todos los que hay en la DLQ al empezar

Registra cada mensaje movido. El trigger puede estar encendido o apagado: si está encendido,
procesa los mensajes en cuanto llegan; si no, esperan en la cola.
"""

import argparse
import logging
import sys

import pika
from pika.exceptions import AMQPError

from app.config import get_settings
from app.infrastructure.rabbitmq.dlq_replayer import DeadLetterReplayer, DlqReplayError
from app.infrastructure.rabbitmq.topology import NOTIFICATION_TOPOLOGY, declare_topology

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.replay_dlq",
        description="Devuelve mensajes de la DLQ a la cola de notificaciones.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="mover todos los mensajes que hay en la DLQ (sin esta opción se mueve uno solo)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    logging.getLogger("pika").setLevel(logging.CRITICAL)

    parameters = pika.URLParameters(settings.rabbitmq_url)
    parameters.socket_timeout = settings.rabbitmq_timeout_seconds
    parameters.stack_timeout = settings.rabbitmq_timeout_seconds
    parameters.connection_attempts = 1
    # En los dos except se usa logger.error y no logger.exception: son fallos esperados (RabbitMQ
    # apagado, mensaje que RabbitMQ no acepta) y el mensaje ya dice qué pasó; el traceback de pika
    # solo agregaría ruido a la salida de un comando que el equipo ejecuta a mano.
    try:
        connection = pika.BlockingConnection(parameters)
    except (AMQPError, OSError) as exc:
        logger.error(
            "No se pudo conectar con RabbitMQ en %s:%s (%s)", parameters.host, parameters.port, type(exc).__name__
        )
        return 1

    try:
        channel = connection.channel()
        declare_topology(channel)  # por si el trigger nunca arrancó: la DLQ tiene que existir
        replayer = DeadLetterReplayer(channel)
        moved = replayer.replay(limit=None if args.all else 1)
        remaining = replayer.pending()
    except DlqReplayError as exc:
        logger.error("%s", exc)
        return 1
    finally:
        if connection.is_open:
            connection.close()

    if not moved:
        logger.info("La DLQ %s está vacía: no hay mensajes para reprocesar", NOTIFICATION_TOPOLOGY.dead_letter_queue)
    else:
        logger.info(
            "Reprocesamiento terminado: %d mensaje(s) devuelto(s) a %s; quedan %d en la DLQ",
            len(moved),
            NOTIFICATION_TOPOLOGY.queue,
            remaining,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
