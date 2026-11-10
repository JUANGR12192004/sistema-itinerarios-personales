"""Proceso del Outbox Relay (Fase 5, ADR-025).

Se ejecuta aparte de la API, desde la carpeta del servicio:

    python -m app.outbox_relay

Cada ciclo abre una sesión de base de datos nueva, ensambla el OutboxRelay con sus
adaptadores reales (PostgreSQL y RabbitMQ) y procesa un lote. Si un ciclo falla
(por ejemplo, PostgreSQL no está disponible), registra el error y sigue con el
siguiente: el proceso no se detiene. Se detiene con Ctrl+C.

Este archivo es el "punto de ensamblaje" del relay, como dependencies.py lo es de la API.
"""

import logging
import time
from collections.abc import Callable

from sqlalchemy.orm import Session, sessionmaker

from app.application.outbox_relay import OutboxRelay, RelayResult
from app.config import Settings, get_settings
from app.infrastructure.messaging.rabbitmq_event_publisher import RabbitMQEventPublisher
from app.infrastructure.persistence.database import get_session_factory
from app.infrastructure.persistence.outbox_repository import SqlAlchemyOutboxRepository
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork

logger = logging.getLogger(__name__)


def build_relay(session: Session, settings: Settings) -> OutboxRelay:
    """Ensambla el relay: outbox en PostgreSQL y publicación en RabbitMQ (sin cambios, ADR-026)."""
    return OutboxRelay(
        outbox=SqlAlchemyOutboxRepository(session),
        publisher=RabbitMQEventPublisher(
            url=settings.rabbitmq_url,
            timeout_seconds=settings.rabbitmq_timeout_seconds,
        ),
        unit_of_work=SqlAlchemyUnitOfWork(session),
        batch_size=settings.outbox_relay_batch_size,
    )


def run_cycle(session_factory: sessionmaker[Session], settings: Settings) -> RelayResult:
    """Ejecuta un ciclo con una sesión nueva; si algo falla, deshace la transacción."""
    with session_factory() as session:
        try:
            return build_relay(session, settings).run_once()
        except Exception:
            # El rollback libera los bloqueos: los eventos siguen pendientes y se
            # reintentan (los ya publicados en este lote se publicarán otra vez).
            session.rollback()
            raise


def run_loop(
    cycle: Callable[[], RelayResult],
    interval_seconds: float,
    batch_size: int,
    sleep: Callable[[float], None] = time.sleep,
    max_cycles: int | None = None,
) -> None:
    """Repite `cycle` con una pausa entre ciclos.

    Si un ciclo procesó un lote completo (publicados + descartados), probablemente
    quedan más pendientes (por ejemplo, al volver RabbitMQ): el siguiente ciclo empieza
    sin esperar. Los fallos temporales no cuentan: con RabbitMQ caído siempre se espera.
    `max_cycles` solo se usa en las pruebas; en producción el bucle no termina.
    """
    cycles = 0
    while max_cycles is None or cycles < max_cycles:
        cycles += 1
        try:
            result = cycle()
        except Exception:
            # Un ciclo fallido no detiene el proceso (ADR-025)
            logger.error(
                "Falló un ciclo del Outbox Relay; se reintenta en %s s", interval_seconds, exc_info=True
            )
            result = RelayResult()

        if result.published + result.dead < batch_size:
            sleep(interval_seconds)


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # pika registra cada conexión en INFO y cada fallo de conexión en ERROR con traceback
    # (una conexión por evento, ADR-021). Con RabbitMQ caído eso llena la consola en cada
    # ciclo; el relay ya registra cada fallo en una línea (WARNING) con su causa.
    logging.getLogger("pika").setLevel(logging.CRITICAL)
    logger.info(
        "Outbox Relay iniciado: revisa cada %s s, lotes de hasta %d eventos (Ctrl+C para detener)",
        settings.outbox_relay_poll_interval_seconds,
        settings.outbox_relay_batch_size,
    )
    session_factory = get_session_factory()
    try:
        run_loop(
            cycle=lambda: run_cycle(session_factory, settings),
            interval_seconds=settings.outbox_relay_poll_interval_seconds,
            batch_size=settings.outbox_relay_batch_size,
        )
    except KeyboardInterrupt:
        logger.info("Outbox Relay detenido")


if __name__ == "__main__":
    main()
