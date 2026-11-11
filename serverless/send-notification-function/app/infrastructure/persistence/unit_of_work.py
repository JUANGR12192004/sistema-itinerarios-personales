"""Implementación del puerto UnitOfWork con una sesión de SQLAlchemy."""

from sqlalchemy.orm import Session

from app.application.ports import UnitOfWork
from app.infrastructure.persistence.errors import translate_database_errors


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Confirma la transacción de la sesión compartida con el repositorio."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def commit(self) -> None:
        with translate_database_errors():
            self._session.commit()
