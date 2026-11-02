"""Publisher vacío que implementa el puerto EventPublisher sin publicar nada.

En la Fase 4 se reemplaza por RabbitMQEventPublisher. Los casos de uso no cambian
porque dependen del puerto, no de esta implementación.
"""

import logging

from app.application.ports import EventPublisher
from app.domain.itinerary import Itinerary

logger = logging.getLogger(__name__)


class NoopEventPublisher(EventPublisher):
    def publish_itinerary_created(self, itinerary: Itinerary) -> None:
        logger.debug(
            "NoopEventPublisher: ItineraryCreatedEvent no publicado (Fase 4) id=%s",
            itinerary.id,
        )
