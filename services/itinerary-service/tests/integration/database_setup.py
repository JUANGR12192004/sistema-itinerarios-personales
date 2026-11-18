"""Base de datos PROPIA de las pruebas de integración (Fase 11).

Las pruebas no usan la base real del servicio (la de DATABASE_URL), sino otra en el mismo
servidor PostgreSQL con el sufijo "_test" (por ejemplo itinerary_db_test). Así pueden vaciar
sus tablas sin borrar los datos de una demostración, y el Outbox Relay real (que lee la base
real) nunca ve los eventos que crean las pruebas.

Al empezar la sesión de pytest:
1. Comprueba que PostgreSQL responda; si no, devuelve None y las pruebas quedan SKIPPED.
2. Crea la base de pruebas si no existe (CREATE DATABASE no admite transacciones: AUTOCOMMIT).
3. Aplica las migraciones con Alembic (alembic upgrade head) sobre esa base, usando la conexión
   de las pruebas (alembic/env.py la acepta en config.attributes["connection"]).

Un error al crear o migrar la base NO se convierte en SKIPPED: debe verse como fallo.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.exc import OperationalError

# Carpeta alembic/ del servicio (tests/integration/ → raíz del servicio)
ALEMBIC_DIR = Path(__file__).resolve().parents[2] / "alembic"

# Espera máxima (segundos) para conectar. Sin este límite, psycopg espera hasta 130 s por
# cada dirección de localhost (::1 y 127.0.0.1 en Windows) cuando PostgreSQL no está.
CONNECT_TIMEOUT_SECONDS = 2
CONNECT_ARGS = {"connect_timeout": CONNECT_TIMEOUT_SECONDS}


def database_url_for_tests(database_url: str) -> URL:
    """URL de la base de pruebas: la misma del servicio con el sufijo _test en el nombre."""
    url = make_url(database_url)
    return url.set(database=f"{url.database}_test")


def prepare_test_database(database_url: str) -> Engine | None:
    """Crea (si hace falta) y migra la base de pruebas. None si PostgreSQL no responde."""
    admin_engine = create_engine(database_url, isolation_level="AUTOCOMMIT", connect_args=CONNECT_ARGS)
    test_url = database_url_for_tests(database_url)
    try:
        with admin_engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": test_url.database}
            ).scalar()
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{test_url.database}"'))
    except OperationalError:
        return None
    finally:
        admin_engine.dispose()

    engine = create_engine(test_url, connect_args=CONNECT_ARGS)
    _migrate(engine)
    return engine


def _migrate(engine: Engine) -> None:
    # Config sin archivo .ini: así Alembic no reconfigura el logging de pytest (fileConfig
    # desactivaría los loggers que usan otras pruebas).
    config = Config()
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
