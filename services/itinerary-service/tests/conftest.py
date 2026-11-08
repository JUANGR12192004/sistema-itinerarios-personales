"""Configuración común de pytest para Itinerary Service.

pytest carga este archivo antes de importar los módulos de prueba, es decir, antes de
que se importe la aplicación (app.main crea la configuración al importarse).

DATABASE_URL no tiene valor por defecto en el servicio (no se dejan credenciales en el
código). Para que las pruebas funcionen recién clonado el repositorio, sin archivo .env,
aquí se define una URL de prueba solo si la configuración no encuentra DATABASE_URL ni en
las variables de entorno ni en el .env. La URL no lleva usuario ni clave: las pruebas de
integración no logran conectarse con ella y quedan SKIPPED; las demás usan fakes.
"""

import os

from pydantic import ValidationError

from app.config import Settings

TEST_DATABASE_URL = "postgresql+psycopg://localhost:5433/itinerary_db"


def database_url_is_missing() -> bool:
    """Indica si la configuración falla únicamente porque falta DATABASE_URL."""
    try:
        Settings()
    except ValidationError as error:
        return any(
            item["loc"] == ("database_url",) and item["type"] == "missing" for item in error.errors()
        )
    return False


if database_url_is_missing():
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
