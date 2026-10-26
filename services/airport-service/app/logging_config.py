"""Configuración básica de logs (los logs JSON llegan en la Fase 9)."""

import logging

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(level: str) -> None:
    """Muestra en la consola los logs del servicio desde el nivel indicado.

    Uvicorn configura solo sus propios loggers. Sin esta configuración, los warnings
    de "app.*" (mapper y Adapter) no tendrían dónde imprimirse.
    """
    app_logger = logging.getLogger("app")
    app_logger.setLevel(level.upper())
    if not app_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        app_logger.addHandler(handler)
