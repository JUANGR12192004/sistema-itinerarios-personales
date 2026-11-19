"""La respuesta de una escritura sale solo DESPUÉS de confirmar la transacción.

Reproduce, sin depender de la velocidad, el fallo intermitente de la prueba E2E
test_crud_completo_por_el_gateway: DELETE respondía 204 y el GET inmediato veía
todavía el itinerario (200 en lugar de 404).

Causa: en FastAPI 0.162 el código que va después del `yield` de una dependencia
(alcance "request", el valor por defecto) se ejecuta DESPUÉS de enviar la
respuesta. Si el commit vive ahí, el cliente recibe la respuesta antes de que
los cambios estén confirmados en PostgreSQL.

Cómo se prueba: se usa el `get_db_session` real con una sesión falsa que anota
`commit`, `rollback` y `close` en una lista, y se envuelve la aplicación en un
middleware ASGI que anota `response_start` cuando sale la respuesta. Así se
compara el ORDEN de los dos hechos, no los tiempos.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

import app.api.dependencies as dependencies
from app.api.dependencies import get_airport_catalog, get_db_session, get_itinerary_repository
from app.domain.itinerary import Itinerary
from app.main import app
from tests.fakes import FakeAirportCatalog, FakeItineraryRepository

FUTURE = datetime.now(timezone.utc) + timedelta(days=30)

BODY_VALIDO = {
    "traveler_name": "Ana Actualizada",
    "departure_airport_id": 1,
    "arrival_airport_id": 5,
    "travel_date": FUTURE.isoformat(),
    "duration_minutes": 90,
}


class RecordingSession:
    """Sesión falsa: solo anota qué operaciones de transacción recibe y en qué orden."""

    def __init__(self, events: list[str]) -> None:
        self._events = events

    def commit(self) -> None:
        self._events.append("commit")

    def rollback(self) -> None:
        self._events.append("rollback")

    def close(self) -> None:
        self._events.append("close")


class RecordResponseStart:
    """Middleware ASGI que anota el momento en que la respuesta sale hacia el cliente."""

    def __init__(self, asgi_app, events: list[str]) -> None:
        self._app = asgi_app
        self._events = events

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def recording_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                self._events.append("response_start")
            await send(message)

        await self._app(scope, receive, recording_send)


@pytest.fixture
def events() -> list[str]:
    return []


@pytest.fixture
def itinerary() -> Itinerary:
    return Itinerary.create(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=FUTURE,
        duration_minutes=75,
    )


@pytest.fixture
def client(monkeypatch, events: list[str], itinerary: Itinerary):
    """Cliente con el get_db_session REAL sobre una sesión que registra el orden.

    El repositorio y el catálogo son falsos, pero el repositorio sigue pidiendo
    get_db_session (como el real), y la unidad de trabajo es la real
    (SqlAlchemyUnitOfWork), que llama a session.commit().
    """
    monkeypatch.setattr(
        dependencies, "get_session_factory", lambda: lambda: RecordingSession(events)
    )

    repo = FakeItineraryRepository()
    repo.save(itinerary)

    def fake_repository(_session=Depends(get_db_session)) -> FakeItineraryRepository:
        return repo

    app.dependency_overrides[get_itinerary_repository] = fake_repository
    app.dependency_overrides[get_airport_catalog] = lambda: FakeAirportCatalog(existing_ids={1, 5})
    yield TestClient(RecordResponseStart(app, events), raise_server_exceptions=False)
    app.dependency_overrides.clear()


def test_delete_confirma_antes_de_responder(client, events, itinerary):
    response = client.delete(f"/itineraries/{itinerary.id}")

    assert response.status_code == 204
    assert "commit" in events
    assert events.index("commit") < events.index("response_start"), events


def test_put_confirma_antes_de_responder(client, events, itinerary):
    response = client.put(f"/itineraries/{itinerary.id}", json=BODY_VALIDO)

    assert response.status_code == 200
    assert "commit" in events
    assert events.index("commit") < events.index("response_start"), events


def test_delete_inexistente_deshace_sin_commit(client, events):
    response = client.delete("/itineraries/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert "commit" not in events
    assert "rollback" in events


def test_put_con_aeropuerto_inexistente_deshace_sin_commit(client, events, itinerary):
    response = client.put(
        f"/itineraries/{itinerary.id}", json={**BODY_VALIDO, "arrival_airport_id": 99}
    )

    assert response.status_code == 422
    assert "commit" not in events
    assert "rollback" in events


def test_la_sesion_siempre_se_cierra(client, events, itinerary):
    client.delete(f"/itineraries/{itinerary.id}")

    assert events[-1] == "close"
