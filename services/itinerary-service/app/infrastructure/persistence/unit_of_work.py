"""Implementación del puerto UnitOfWork con una sesión de SQLAlchemy."""

from sqlalchemy.orm import Session

from app.application.ports import UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Confirma la transacción de la sesión compartida con el repositorio.

    FastAPI entrega la MISMA sesión por solicitud al repositorio y a esta clase,
    así que `commit()` confirma lo que el repositorio guardó. El commit final de
    `get_db_session` sigue existiendo para las demás rutas; si ya no hay cambios
    pendientes, no hace nada.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def commit(self) -> None:
        self._session.commit()
