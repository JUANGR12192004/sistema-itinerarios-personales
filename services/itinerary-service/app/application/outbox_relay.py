"""Outbox Relay: publica en RabbitMQ los eventos pendientes de la outbox (ADR-025).

Es lógica de aplicación: solo depende de puertos (OutboxRepository, EventPublisher,
UnitOfWork), así que se prueba con fakes. El proceso que lo ejecuta en bucle
está en app/outbox_relay.py.

Cada ciclo (`run_once`) procesa un lote dentro de UNA transacción:
1. Toma hasta `batch_size` pendientes (bloqueados para este relay).
2. Por cada uno: reconstruye el evento, lo publica y lo marca como publicado.
3. Hace commit: se guardan las marcas y se liberan los bloqueos.

Garantía "al menos una vez": primero se publica y después se marca. Si el proceso
se detiene entre la publicación y el commit, la marca se pierde y el evento se
publicará otra vez. Por eso el consumidor debe ser idempotente con `event_id`.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from app.application.events import ItineraryCreatedEvent
from app.application.exceptions import EventPublishError
from app.application.outbox import OutboxMessage
from app.application.ports import EventPublisher, OutboxRepository, UnitOfWork

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RelayResult:
    """Resumen de un ciclo del relay."""

    published: int = 0
    failed: int = 0


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OutboxRelay:
    def __init__(
        self,
        outbox: OutboxRepository,
        publisher: EventPublisher,
        unit_of_work: UnitOfWork,
        batch_size: int,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._outbox = outbox
        self._publisher = publisher
        self._unit_of_work = unit_of_work
        self._batch_size = batch_size
        self._clock = clock

    def run_once(self) -> RelayResult:
        """Procesa un lote de pendientes y confirma el resultado con un solo commit."""
        published = 0
        failed = 0

        for message in self._outbox.get_pending(self._batch_size):
            try:
                event = _to_event(message)
            except (KeyError, TypeError, ValueError) as exc:
                # El mensaje está mal formado: reintentarlo no lo arreglará y no depende
                # de RabbitMQ, así que se marca como fallido y se sigue con el siguiente.
                self._outbox.mark_failed(message.id, f"Mensaje ilegible: {exc!r}")
                failed += 1
                logger.error(
                    "Mensaje de la outbox ilegible (id=%s, event_type=%s): %r",
                    message.id,
                    message.event_type,
                    exc,
                )
                continue

            try:
                self._publisher.publish(event)
            except EventPublishError as exc:
                # Lo más probable es que RabbitMQ no esté disponible: se registra el fallo
                # y se detiene el lote. Los demás siguen pendientes, sin sumar intentos.
                self._outbox.mark_failed(message.id, str(exc))
                failed += 1
                logger.warning(
                    "No se pudo publicar el evento %s (intento %d): %s. "
                    "Se detiene el lote; se reintenta en el siguiente ciclo",
                    message.id,
                    message.attempts + 1,
                    exc,
                )
                break

            self._outbox.mark_published(message.id, self._clock())
            published += 1

        self._unit_of_work.commit()

        if published or failed:
            logger.info("Ciclo del Outbox Relay: %d publicados, %d fallidos", published, failed)
        return RelayResult(published=published, failed=failed)


def _to_event(message: OutboxMessage) -> ItineraryCreatedEvent:
    """Reconstruye el evento de integración guardado en la outbox."""
    if message.event_type != ItineraryCreatedEvent.EVENT_TYPE:
        raise ValueError(f"event_type desconocido: {message.event_type!r}")
    return ItineraryCreatedEvent.from_dict(message.payload)
