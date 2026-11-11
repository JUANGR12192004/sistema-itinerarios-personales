"""Pruebas de la traducción de errores de PostgreSQL a TransientError (ADR-028).

No necesitan PostgreSQL: usan un engine que apunta a un puerto donde no hay nada
(127.0.0.1:1), así que la conexión falla igual que con PostgreSQL apagado.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.orm import sessionmaker

from app.application.exceptions import TransientError
from app.domain.notification_record import NotificationRecord
from app.handler import run_use_case
from app.infrastructure.persistence.database import get_engine
from app.infrastructure.persistence.errors import translate_database_errors
from app.infrastructure.persistence.repository import SqlAlchemyNotificationHistoryRepository
from tests.samples import make_event

# Nadie escucha en el puerto 1: la conexión se rechaza (como PostgreSQL apagado)
UNREACHABLE_DATABASE_URL = "postgresql+psycopg://notification:notification@127.0.0.1:1/notification_db"


@pytest.fixture(scope="module")
def unreachable_session_factory():
    engine = create_engine(UNREACHABLE_DATABASE_URL, connect_args={"connect_timeout": 2})
    yield sessionmaker(bind=engine)
    engine.dispose()


def _record() -> NotificationRecord:
    event = make_event()
    return NotificationRecord.create(
        event_id=event.event_id,
        itinerary_id=event.itinerary_id,
        recipient=event.traveler_email,
        message="Hola",
        correlation_id=event.correlation_id,
        processed_at=event.occurred_at,
    )


def test_el_engine_no_muestra_los_parametros_del_sql_en_los_errores():
    """Los errores de SQLAlchemy llegan al log de la función: no deben llevar el correo ni el nombre."""
    assert get_engine().hide_parameters is True


def test_un_error_de_conexion_se_convierte_en_transient_error():
    original = OperationalError("INSERT ...", {}, Exception("connection refused"))

    with pytest.raises(TransientError) as error:
        with translate_database_errors():
            raise original

    assert error.value.__cause__ is original  # se conserva el error original para el log


@pytest.mark.parametrize(
    "other_error",
    [
        ProgrammingError("INSERT ...", {}, Exception('relation "notification_history" does not exist')),
        IntegrityError("INSERT ...", {}, Exception("violates check constraint")),
        ValueError("error de programación"),
    ],
)
def test_los_demas_errores_no_se_convierten(other_error):
    with pytest.raises(type(other_error)):
        with translate_database_errors():
            raise other_error


def test_el_repositorio_informa_transient_error_si_postgresql_no_responde(unreachable_session_factory):
    """La conexión se abre en la primera consulta (el INSERT de add_if_absent), antes del commit."""
    record = _record()
    with unreachable_session_factory() as session:
        repository = SqlAlchemyNotificationHistoryRepository(session)

        with pytest.raises(TransientError):
            repository.add_if_absent(record)


def test_run_use_case_informa_transient_error_si_postgresql_no_responde(unreachable_session_factory):
    """Toda la ejecución del caso de uso queda envuelta: el handler lanza TransientError."""
    event = make_event()
    with pytest.raises(TransientError):
        run_use_case(event, session_factory=unreachable_session_factory)
