"""Implementación del puerto UnitOfWork con una sesión de SQLAlchemy."""

from sqlalchemy.orm import Session

from app.application.ports import UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Confirma la transacción de la sesión compartida con el repositorio.

    FastAPI entrega la MISMA sesión por solicitud al repositorio y a esta clase,
    así que `commit()` confirma lo que el repositorio guardó. Es el ÚNICO commit de
    la API: lo llaman los casos de uso de crear, actualizar y eliminar antes de
    devolver el resultado, así la respuesta HTTP sale con los cambios ya confirmados.
    `get_db_session` solo deshace (rollback) si hay error y cierra la sesión.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def commit(self) -> None:
        self._session.commit()
