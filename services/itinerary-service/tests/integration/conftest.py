"""Fixtures de infraestructura para las pruebas de integración.

pg_engine        — engine de sesión; yield None si PostgreSQL no está disponible.
db_session       — sesión por prueba con limpieza de itineraries y outbox_events.
rabbitmq_channel — canal real con la topología declarada y la cola vacía.

Cada fixture hace SKIPPED la prueba si su dependencia no está disponible.
"""

import pika
import pytest
from pika.exceptions import AMQPError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.infrastructure.messaging.topology import QUEUE_NOTIFICATIONS, declare_topology

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


@pytest.fixture
def rabbitmq_channel():
    """Canal real con la topología declarada y la cola vacía; SKIPPED si no hay RabbitMQ.

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
    declare_topology(channel)
    channel.queue_purge(QUEUE_NOTIFICATIONS)

    yield channel

    channel.queue_purge(QUEUE_NOTIFICATIONS)
    connection.close()
