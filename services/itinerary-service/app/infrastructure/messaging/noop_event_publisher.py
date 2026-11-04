"""Publisher vacío que implementa el puerto EventPublisher sin publicar nada.

En la entrega 4B se reemplaza por RabbitMQEventPublisher en `dependencies.py`.
Los casos de uso no cambian porque dependen del puerto, no de esta implementación.
"""

import logging

from app.application.events import ItineraryCreatedEvent
from app.application.ports import EventPublisher

logger = logging.getLogger(__name__)


class NoopEventPublisher(EventPublisher):
    def publish(self, event: ItineraryCreatedEvent) -> None:
        logger.debug(
            "NoopEventPublisher: %s no publicado event_id=%s itinerary_id=%s",
            event.EVENT_TYPE,
            event.event_id,
            event.itinerary_id,
        )
