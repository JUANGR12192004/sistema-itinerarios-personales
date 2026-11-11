"""Adaptador que simula el envío de un correo (canal `simulated-email`).

El proyecto no envía correos reales: el "envío" es una línea de log con el destinatario
y el mensaje, visible con `docker logs send-notification-function`. Para enviar correos
de verdad bastaría con otro adaptador del mismo puerto (por ejemplo, con Amazon SES),
sin cambiar el caso de uso.
"""

import logging

from app.application.ports import NotificationSender

logger = logging.getLogger(__name__)


class SimulatedEmailSender(NotificationSender):
    """Implementa NotificationSender escribiendo el correo en el log."""

    def send(self, recipient: str, message: str) -> None:
        logger.info("Correo simulado enviado a %s: %s", recipient, message)
