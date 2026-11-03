"""Pruebas de integración de SqlAlchemyItineraryRepository contra PostgreSQL real.

Verifican que el repositorio persiste y recupera datos correctamente,
incluidos traveler_email = None y travel_date con zona horaria.

Se omiten automáticamente (SKIPPED) cuando PostgreSQL no está disponible;
el fixture db_session (conftest.py) se encarga de llamar pytest.skip().
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.domain.itinerary import Itinerary
from app.infrastructure.persistence.repository import SqlAlchemyItineraryRepository

FUTURE = datetime.now(timezone.utc) + timedelta(days=30)


def _crear_itinerario(**overrides) -> Itinerary:
    defaults = dict(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=FUTURE,
        duration_minutes=75,
    )
    defaults.update(overrides)
    return Itinerary.create(**defaults)


def test_guardar_y_obtener_por_id_sin_email(db_session):
    """traveler_email = None se persiste y se recupera como None."""
    repo = SqlAlchemyItineraryRepository(db_session)
    it = _crear_itinerario()
    repo.save(it)
    db_session.commit()

    resultado = repo.get_by_id(it.id)
    assert resultado is not None
    assert resultado.id == it.id
    assert resultado.traveler_name == "Ana Pérez"
    assert resultado.traveler_email is None


def test_guardar_con_email_y_travel_date_con_zona_horaria(db_session):
    """Verifica que traveler_email y travel_date (con offset) se persisten correctamente.

    PostgreSQL normaliza TIMESTAMP WITH TIME ZONE a UTC; comparamos el instante
    UTC equivalente para no depender de la zona horaria del servidor.
    """
    repo = SqlAlchemyItineraryRepository(db_session)
    fecha_con_offset = datetime(2027, 6, 15, 8, 0, 0, tzinfo=timezone(timedelta(hours=-5)))
    it = _crear_itinerario(
        traveler_name="Carlos López",
        traveler_email="carlos@example.com",
        travel_date=fecha_con_offset,
        duration_minutes=120,
    )
    repo.save(it)
    db_session.commit()

    resultado = repo.get_by_id(it.id)
    assert resultado.traveler_email == "carlos@example.com"
    assert resultado.travel_date.tzinfo is not None
    # Comparar instantes en UTC (PostgreSQL normaliza al almacenar)
    assert resultado.travel_date.utctimetuple() == fecha_con_offset.utctimetuple()


def test_obtener_id_inexistente_devuelve_none(db_session):
    repo = SqlAlchemyItineraryRepository(db_session)
    assert repo.get_by_id(uuid4()) is None


def test_listar_vacio(db_session):
    repo = SqlAlchemyItineraryRepository(db_session)
    assert repo.list_all() == []


def test_listar_todos(db_session):
    repo = SqlAlchemyItineraryRepository(db_session)
    repo.save(_crear_itinerario(traveler_name="Viajero Uno"))
    repo.save(_crear_itinerario(
        traveler_name="Viajero Dos",
        departure_airport_id=2,
        arrival_airport_id=6,
    ))
    db_session.commit()

    resultado = repo.list_all()
    assert len(resultado) == 2
    nombres = {it.traveler_name for it in resultado}
    assert nombres == {"Viajero Uno", "Viajero Dos"}


def test_actualizar_itinerario(db_session):
    """save() sobre un id existente actualiza los campos (no duplica la fila)."""
    repo = SqlAlchemyItineraryRepository(db_session)
    it = _crear_itinerario()
    repo.save(it)
    db_session.commit()

    it.update(
        traveler_name="Nombre Actualizado",
        departure_airport_id=it.departure_airport_id,
        arrival_airport_id=it.arrival_airport_id,
        travel_date=it.travel_date,
        duration_minutes=90,
        traveler_email="nuevo@example.com",
    )
    repo.save(it)
    db_session.commit()

    resultado = repo.get_by_id(it.id)
    assert resultado.traveler_name == "Nombre Actualizado"
    assert resultado.duration_minutes == 90
    assert resultado.traveler_email == "nuevo@example.com"
    assert len(repo.list_all()) == 1  # sigue siendo uno, no se duplicó


def test_eliminar_itinerario(db_session):
    repo = SqlAlchemyItineraryRepository(db_session)
    it = _crear_itinerario()
    repo.save(it)
    db_session.commit()

    repo.delete(it.id)
    db_session.commit()

    assert repo.get_by_id(it.id) is None
    assert repo.list_all() == []


def test_eliminar_id_inexistente_no_lanza(db_session):
    repo = SqlAlchemyItineraryRepository(db_session)
    repo.delete(uuid4())  # no debe lanzar excepción
    db_session.commit()
