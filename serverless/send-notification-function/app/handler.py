"""Handler de AWS Lambda de SendNotificationFunction (ADR-008 y ADR-028).

La plataforma (en local, el Runtime Interface Emulator) llama a `handler(event, context)`
cada vez que alguien invoca la función:

    POST http://localhost:9000/2015-03-31/functions/function/invocations   (cuerpo = event)

El handler es el ADAPTADOR DE ENTRADA, como una ruta FastAPI en los servicios:
1. Valida el evento contra el contrato v1 (app/event_schema.py).
2. Ensambla y ejecuta el caso de uso con sus adaptadores reales.
3. Convierte el resultado en la respuesta de la función.

Contrato con quien la invoca (el Event Trigger, entrega 6B):
- Respuestas: PROCESSED, ALREADY_PROCESSED o REJECTED (evento inválido, fallo permanente).
- PostgreSQL no disponible: lanza TransientError; el RIE responde
  {"errorType": "TransientError", "errorMessage": "..."}.
- Cualquier otro error no se captura: el RIE lo informa con el nombre de su clase.

La función no conoce RabbitMQ y no guarda estado entre invocaciones: solo reutiliza
el engine de SQLAlchemy mientras el contenedor siga caliente.
"""

import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.application.events import ItineraryCreatedEvent
from app.application.exceptions import InvalidEventError
from app.application.use_cases import (
    NotificationResult,
    NotifyItineraryCreatedUseCase,
    ProcessingStatus,
)
from app.config import get_settings
from app.event_schema import parse_event
from app.infrastructure.notification.simulated_email_sender import SimulatedEmailSender
from app.infrastructure.persistence.database import get_session_factory
from app.infrastructure.persistence.errors import translate_database_errors
from app.infrastructure.persistence.repository import SqlAlchemyNotificationHistoryRepository
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork

logger = logging.getLogger(__name__)

RunUseCase = Callable[[ItineraryCreatedEvent], NotificationResult]


def handler(event: Any, context: Any) -> dict[str, Any]:
    """Punto de entrada que llama la plataforma Lambda (CMD ["app.handler.handler"])."""
    _configure_logging()
    logger.info("Invocación recibida: aws_request_id=%s", getattr(context, "aws_request_id", None))
    return process_event(event, run_use_case)


def process_event(event: Any, run: RunUseCase) -> dict[str, Any]:
    """Valida el evento, ejecuta el caso de uso y arma la respuesta.

    `run` se recibe como parámetro para probar el handler con un caso de uso falso.
    """
    try:
        notification_event = parse_event(event)
    except InvalidEventError as error:
        logger.warning(
            "Evento rechazado (fallo permanente): event_id=%s motivo=%s",
            error.event_id,
            error.reason,
        )
        return {
            "status": ProcessingStatus.REJECTED.value,
            "event_id": str(error.event_id) if error.event_id else None,
            "reason": error.reason,
        }

    return _to_response(run(notification_event))


def run_use_case(
    event: ItineraryCreatedEvent,
    session_factory: sessionmaker[Session] | None = None,
) -> NotificationResult:
    """Ejecuta el caso de uso con PostgreSQL y el correo simulado, en una sesión por invocación.

    translate_database_errors envuelve TODA la ejecución, no solo el commit: la conexión se
    abre en la primera consulta (el INSERT de add_if_absent) y también puede fallar al cerrar
    la sesión. Con PostgreSQL apagado, cualquiera de esos fallos sale como TransientError.
    Al salir del `with` la sesión se cierra; si no hubo commit, sus cambios se deshacen.
    """
    factory = session_factory or get_session_factory()
    with translate_database_errors():
        with factory() as session:
            return build_use_case(session).execute(event)


def build_use_case(session: Session) -> NotifyItineraryCreatedUseCase:
    """Ensambla el caso de uso: repositorio y unit of work comparten la misma sesión."""
    return NotifyItineraryCreatedUseCase(
        history=SqlAlchemyNotificationHistoryRepository(session),
        sender=SimulatedEmailSender(),
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


def _to_response(result: NotificationResult) -> dict[str, Any]:
    response: dict[str, Any] = {"status": result.status.value, "event_id": str(result.event_id)}
    if result.status is ProcessingStatus.PROCESSED:
        response["notification_id"] = str(result.notification_id)
        response["notification_status"] = (
            result.notification_status.value if result.notification_status else None
        )
    return response


def _configure_logging() -> None:
    """Muestra los logs de `app` con el nivel configurado.

    En Lambda el runtime ya instala un handler en el logger raíz (los logs salen por la
    salida estándar: `docker logs` en local, CloudWatch en AWS); basicConfig solo actúa
    si no hay ninguno, por ejemplo al ejecutar el handler fuera de Lambda.
    """
    logging.basicConfig(format="%(levelname)s [%(name)s] %(message)s")
    logging.getLogger("app").setLevel(get_settings().log_level.upper())
