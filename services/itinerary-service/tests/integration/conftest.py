"""Fixtures de infraestructura para las pruebas de integración.

pg_engine                  — engine de sesión; yield None si PostgreSQL no está disponible.
db_session                 — sesión por prueba con limpieza de itineraries y outbox_events.
rabbitmq_parameters        — parámetros de conexión; SKIPPED (una sola vez) si RabbitMQ no responde.
rabbitmq_channel           — canal real para cada prueba.
isolated_topology          — topología de prueba (exchange, cola, DLX y DLQ) con sus colas vacías.
isolated_publisher         — RabbitMQEventPublisher que publica en el exchange de prueba.
unbound_notification_queue — desenlaza la cola de prueba durante la prueba (como si el Event
                             Trigger no hubiera arrancado) y la vuelve a enlazar al final.

Cada fixture hace SKIPPED la prueba si su dependencia no está disponible.

AISLAMIENTO DE RABBITMQ: las pruebas NO tocan la cola real notification.itinerary-created ni su
DLQ (mismo criterio que las del Event Trigger, entrega 6C). Usan su propia topología con nombres
únicos (prefijo `test-<id>.`) y los mismos argumentos que la real: se declara una vez por sesión de
pytest, sus colas se vacían antes y después de cada prueba, y se borra al terminar la sesión. Así se
pueden correr durante una demostración sin vaciar ni desenlazar las colas reales. Se declara una
sola vez porque en RabbitMQ declarar y borrar colas tarda.

LIMITACIÓN (base de datos, pendiente en CLAUDE.md): db_session usa la base real itinerary_db y
BORRA todas las filas de itineraries y outbox_events antes y después de cada prueba. Además, si el
Outbox Relay real está encendido, puede publicar en la cola real los eventos que crean las pruebas.
Antes de correrlas: detener el Outbox Relay y no tener datos de demostración que se quieran conservar.
"""

from dataclasses import dataclass
from uuid import uuid4

import pika
import pytest
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.infrastructure.messaging.rabbitmq_event_publisher import RabbitMQEventPublisher
from app.infrastructure.messaging.topology import (
    EXCHANGE,
    ROUTING_KEY_ITINERARY_CREATED,
    declare_exchange,
)

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


@dataclass(frozen=True)
class IsolatedTopology:
    """Nombres de la topología de prueba (los mismos campos que QueueTopology del Event Trigger)."""

    exchange: str
    routing_key: str
    queue: str
    dead_letter_exchange: str
    dead_letter_queue: str


def declare_notification_queue(channel: BlockingChannel, topology: IsolatedTopology) -> None:
    """Declara la parte del consumidor (cola, DLX, DLQ y bindings) con los mismos argumentos que el
    Event Trigger (serverless/event-trigger/app/infrastructure/rabbitmq/topology.py). Desde la
    Fase 6 (ADR-032) esa parte es del trigger: Itinerary Service solo declara su exchange."""
    channel.exchange_declare(exchange=topology.dead_letter_exchange, exchange_type="direct", durable=True)
    channel.queue_declare(queue=topology.dead_letter_queue, durable=True)
    channel.queue_bind(
        queue=topology.dead_letter_queue, exchange=topology.dead_letter_exchange, routing_key=topology.routing_key
    )
    channel.queue_declare(
        queue=topology.queue,
        durable=True,
        arguments={"x-dead-letter-exchange": topology.dead_letter_exchange},
    )
    channel.queue_bind(queue=topology.queue, exchange=topology.exchange, routing_key=topology.routing_key)


@pytest.fixture(scope="session")
def rabbitmq_parameters() -> pika.URLParameters:
    """Comprueba una vez si RabbitMQ responde; si no, todas las pruebas que lo usan quedan SKIPPED."""
    parameters = pika.URLParameters(get_settings().rabbitmq_url)
    parameters.socket_timeout = RABBITMQ_TIMEOUT_SECONDS
    parameters.stack_timeout = RABBITMQ_TIMEOUT_SECONDS
    parameters.connection_attempts = 1
    try:
        pika.BlockingConnection(parameters).close()
    except (AMQPError, OSError):
        pytest.skip("RabbitMQ no disponible — omitiendo prueba de integración")
    return parameters


@pytest.fixture(scope="session")
def _session_topology(rabbitmq_parameters):
    """Topología con nombres únicos para esta sesión; se borra al final, pase lo que pase."""
    prefix = f"test-{uuid4().hex[:8]}."
    topology = IsolatedTopology(
        exchange=prefix + EXCHANGE,
        routing_key=ROUTING_KEY_ITINERARY_CREATED,
        queue=prefix + "notification.itinerary-created",
        dead_letter_exchange=prefix + "itinerary.events.dlx",
        dead_letter_queue=prefix + "notification.itinerary-created.dlq",
    )
    connection = pika.BlockingConnection(rabbitmq_parameters)
    channel = connection.channel()
    declare_exchange(channel, topology.exchange)
    declare_notification_queue(channel, topology)
    connection.close()
    try:
        yield topology
    finally:
        _delete_topology(rabbitmq_parameters, topology)


def _delete_topology(parameters: pika.URLParameters, topology: IsolatedTopology) -> None:
    """Borra las colas y exchanges de prueba con una conexión nueva."""
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_delete(queue=topology.queue)
    channel.queue_delete(queue=topology.dead_letter_queue)
    channel.exchange_delete(exchange=topology.exchange)
    channel.exchange_delete(exchange=topology.dead_letter_exchange)
    connection.close()


@pytest.fixture
def rabbitmq_channel(rabbitmq_parameters):
    """Canal real para cada prueba; SKIPPED si no hay RabbitMQ."""
    connection = pika.BlockingConnection(rabbitmq_parameters)
    yield connection.channel()
    if connection.is_open:
        connection.close()


@pytest.fixture
def isolated_topology(rabbitmq_channel, _session_topology):
    """La topología de prueba con sus dos colas vacías (solo se vacían las colas de prueba)."""
    _purge(rabbitmq_channel, _session_topology)
    yield _session_topology
    if rabbitmq_channel.is_open:
        _purge(rabbitmq_channel, _session_topology)


def _purge(channel: BlockingChannel, topology: IsolatedTopology) -> None:
    channel.queue_purge(topology.queue)
    channel.queue_purge(topology.dead_letter_queue)


@pytest.fixture
def isolated_publisher(isolated_topology) -> RabbitMQEventPublisher:
    """El publicador real de Itinerary Service, apuntando al exchange de prueba."""
    return RabbitMQEventPublisher(
        get_settings().rabbitmq_url, RABBITMQ_TIMEOUT_SECONDS, exchange=isolated_topology.exchange
    )


@pytest.fixture
def unbound_notification_queue(rabbitmq_channel, isolated_topology):
    """Quita el binding de la cola de prueba durante la prueba.

    Simula que el Event Trigger nunca arrancó: el exchange existe, pero no tiene a qué cola
    entregar. Solo se desenlaza la cola de prueba (la real no se toca) y al final se vuelve a
    enlazar, porque la topología de prueba se reutiliza en toda la sesión.
    """
    rabbitmq_channel.queue_unbind(
        queue=isolated_topology.queue, exchange=isolated_topology.exchange, routing_key=isolated_topology.routing_key
    )
    try:
        yield isolated_topology
    finally:
        if rabbitmq_channel.is_open:
            rabbitmq_channel.queue_bind(
                queue=isolated_topology.queue,
                exchange=isolated_topology.exchange,
                routing_key=isolated_topology.routing_key,
            )
