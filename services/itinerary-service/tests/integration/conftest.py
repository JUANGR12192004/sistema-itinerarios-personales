"""Fixtures de infraestructura para las pruebas de integración.

pg_engine                  — engine de sesión; yield None si PostgreSQL no está disponible.
db_session                 — sesión por prueba con limpieza de itineraries y outbox_events.
rabbitmq_channel           — canal real con el exchange y la cola de notificaciones declarados
                             y la cola vacía.
unbound_notification_queue — desenlaza la cola durante la prueba (como si el Event Trigger
                             no hubiera arrancado) y la vuelve a enlazar al final.

Cada fixture hace SKIPPED la prueba si su dependencia no está disponible.
"""

import pika
import pytest
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.infrastructure.messaging.topology import (
    EXCHANGE,
    ROUTING_KEY_ITINERARY_CREATED,
    declare_exchange,
)

# Desde la Fase 6 (ADR-032) la cola de notificaciones es del Event Trigger: Itinerary Service
# ya no la declara. Las pruebas la declaran aquí, en el papel del consumidor, con los mismos
# argumentos que usa el trigger (serverless/event-trigger/app/infrastructure/rabbitmq/topology.py).
QUEUE_NOTIFICATIONS = "notification.itinerary-created"
DEAD_LETTER_EXCHANGE = "itinerary.events.dlx"
DEAD_LETTER_QUEUE = "notification.itinerary-created.dlq"

# Espera máxima (segundos) para conectar y operar con RabbitMQ en las pruebas
RABBITMQ_TIMEOUT_SECONDS = 2.0

# Espera máxima (segundos) para comprobar si PostgreSQL está disponible. Sin este límite,
# psycopg espera hasta 130 s por cada dirección de localhost (::1 y 127.0.0.1 en Windows).
CONNECT_TIMEOUT_SECONDS = 2


@pytest.fixture(scope="session")
def pg_engine():
    """Crea el engine una sola vez por sesión de pytest.

    Si PostgreSQL no responde, devuelve None; db_session se encarga de saltar
    cada prueba individualmente para que aparezcan como SKIPPED en el reporte.
    """
    settings = get_settings()
    try:
        engine = create_engine(
            settings.database_url,
            connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        yield engine
        engine.dispose()
    except Exception:
        yield None


@pytest.fixture
def db_session(pg_engine):
    """Sesión limpia para cada prueba.

    Si pg_engine es None (PostgreSQL no disponible) la prueba se marca como
    SKIPPED, no como FAILED, para que el CI siga en verde sin base de datos.

    Limpieza: elimina todos los registros de itineraries y outbox_events antes y
    después de cada prueba para garantizar aislamiento entre tests. Requiere las
    migraciones aplicadas (`alembic upgrade head`).
    """
    if pg_engine is None:
        pytest.skip("PostgreSQL no disponible — omitiendo prueba de integración")

    session = Session(pg_engine)
    _clean_tables(session)

    yield session

    session.rollback()  # por si la prueba dejó una transacción a medias
    _clean_tables(session)
    session.close()


def _clean_tables(session: Session) -> None:
    session.execute(text("DELETE FROM outbox_events"))
    session.execute(text("DELETE FROM itineraries"))
    session.commit()


def declare_notification_queue(channel: BlockingChannel) -> None:
    """Declara la parte del consumidor (cola, DLX, DLQ y bindings), como lo hace el Event Trigger."""
    channel.exchange_declare(exchange=DEAD_LETTER_EXCHANGE, exchange_type="direct", durable=True)
    channel.queue_declare(queue=DEAD_LETTER_QUEUE, durable=True)
    channel.queue_bind(
        queue=DEAD_LETTER_QUEUE, exchange=DEAD_LETTER_EXCHANGE, routing_key=ROUTING_KEY_ITINERARY_CREATED
    )
    channel.queue_declare(
        queue=QUEUE_NOTIFICATIONS,
        durable=True,
        arguments={"x-dead-letter-exchange": DEAD_LETTER_EXCHANGE},
    )
    channel.queue_bind(queue=QUEUE_NOTIFICATIONS, exchange=EXCHANGE, routing_key=ROUTING_KEY_ITINERARY_CREATED)


@pytest.fixture
def rabbitmq_channel():
    """Canal real con el exchange y la cola de notificaciones declarados y la cola vacía;
    SKIPPED si no hay RabbitMQ.

    ATENCIÓN: vacía (purge) la cola notification.itinerary-created antes y después
    de la prueba. No usarlo contra un RabbitMQ con mensajes que se quieran conservar.
    """
    parameters = pika.URLParameters(get_settings().rabbitmq_url)
    parameters.socket_timeout = RABBITMQ_TIMEOUT_SECONDS
    parameters.stack_timeout = RABBITMQ_TIMEOUT_SECONDS
    parameters.connection_attempts = 1
    try:
        connection = pika.BlockingConnection(parameters)
    except (AMQPError, OSError):
        pytest.skip("RabbitMQ no disponible — omitiendo prueba de integración")

    channel = connection.channel()
    declare_exchange(channel)
    declare_notification_queue(channel)
    channel.queue_purge(QUEUE_NOTIFICATIONS)

    yield channel

    channel.queue_purge(QUEUE_NOTIFICATIONS)
    connection.close()


@pytest.fixture
def unbound_notification_queue(rabbitmq_channel):
    """Quita el binding de la cola de notificaciones durante la prueba.

    Simula que el Event Trigger nunca arrancó: el exchange existe, pero no tiene a qué cola
    entregar. La cola no se borra (no se pierden sus mensajes) y al final se vuelve a enlazar.
    """
    rabbitmq_channel.queue_unbind(
        queue=QUEUE_NOTIFICATIONS, exchange=EXCHANGE, routing_key=ROUTING_KEY_ITINERARY_CREATED
    )
    try:
        yield rabbitmq_channel
    finally:
        rabbitmq_channel.queue_bind(
            queue=QUEUE_NOTIFICATIONS, exchange=EXCHANGE, routing_key=ROUTING_KEY_ITINERARY_CREATED
        )
