"""Pruebas unitarias de OutboxRelay con fakes, sin PostgreSQL ni RabbitMQ (ADR-025)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.application.events import ItineraryCreatedEvent
from app.application.outbox import OutboxMessage
from app.application.outbox_relay import OutboxRelay, RelayResult
from app.domain.itinerary import Itinerary
from tests.fakes import FakeEventPublisher, FakeOutboxRepository, FakeUnitOfWork

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)


def _message(minutes_ago: int = 0) -> OutboxMessage:
    """Mensaje pendiente con un evento real; `minutes_ago` fija el orden por occurred_at."""
    itinerary = Itinerary.create(
        traveler_name="Ana Pérez",
        departure_airport_id=1,
        arrival_airport_id=5,
        travel_date=datetime.now(timezone.utc) + timedelta(days=30),
        duration_minutes=75,
    )
    event = ItineraryCreatedEvent.from_itinerary(itinerary, "cid-relay")
    message = OutboxMessage.from_event(event)
    message.occurred_at = NOW - timedelta(minutes=minutes_ago)
    return message


def _relay(
    messages: list[OutboxMessage],
    publisher_fails: bool = False,
    batch_size: int = 10,
) -> tuple[OutboxRelay, FakeOutboxRepository, FakeEventPublisher, FakeUnitOfWork]:
    outbox = FakeOutboxRepository(messages)
    publisher = FakeEventPublisher(fail=publisher_fails)
    uow = FakeUnitOfWork()
    relay = OutboxRelay(outbox, publisher, uow, batch_size=batch_size, clock=lambda: NOW)
    return relay, outbox, publisher, uow


def test_publica_los_pendientes_del_mas_antiguo_al_mas_nuevo():
    newest, oldest = _message(minutes_ago=1), _message(minutes_ago=5)
    relay, _, publisher, _ = _relay([newest, oldest])

    result = relay.run_once()

    assert result == RelayResult(published=2, failed=0)
    assert [e.event_id for e in publisher.published] == [oldest.id, newest.id]


def test_marca_los_publicados_y_hace_un_solo_commit():
    message = _message()
    relay, outbox, _, uow = _relay([message])

    relay.run_once()

    assert outbox.messages[message.id].published_at == NOW
    assert uow.commits == 1


def test_publica_el_mismo_evento_que_se_guardo():
    """El evento reconstruido es idéntico al original: mismo event_id (= message_id en AMQP)."""
    message = _message()
    relay, _, publisher, _ = _relay([message])

    relay.run_once()

    assert publisher.published[0].to_dict() == message.payload


def test_respeta_el_tamano_del_lote():
    messages = [_message(minutes_ago=i) for i in range(5)]
    relay, outbox, publisher, _ = _relay(messages, batch_size=2)

    result = relay.run_once()

    assert result.published == 2
    assert len(publisher.published) == 2
    assert len(outbox.get_pending(10)) == 3


def test_sin_pendientes_no_publica_nada():
    relay, _, publisher, _ = _relay([])

    assert relay.run_once() == RelayResult()
    assert publisher.published == []


def test_no_vuelve_a_publicar_los_ya_publicados():
    relay, _, publisher, _ = _relay([_message()])

    relay.run_once()
    second = relay.run_once()

    assert second == RelayResult()
    assert len(publisher.published) == 1


def test_fallo_de_publicacion_suma_intento_y_guarda_el_error():
    message = _message()
    relay, outbox, _, uow = _relay([message], publisher_fails=True)

    result = relay.run_once()

    stored = outbox.messages[message.id]
    assert result == RelayResult(published=0, failed=1)
    assert stored.published_at is None  # sigue pendiente: no se pierde
    assert stored.attempts == 1
    assert "RabbitMQ no disponible" in stored.last_error
    assert uow.commits == 1  # el intento fallido también se guarda


def test_fallo_de_publicacion_detiene_el_lote():
    first, second, third = _message(minutes_ago=3), _message(minutes_ago=2), _message(minutes_ago=1)
    relay, outbox, _, _ = _relay([first, second, third], publisher_fails=True)

    result = relay.run_once()

    assert result.failed == 1
    assert outbox.messages[first.id].attempts == 1
    assert outbox.messages[second.id].attempts == 0
    assert outbox.messages[third.id].attempts == 0


def test_el_evento_fallido_se_publica_en_el_siguiente_ciclo():
    """RabbitMQ vuelve: el mismo evento se publica sin haberse perdido."""
    message = _message()
    relay, outbox, publisher, _ = _relay([message], publisher_fails=True)
    relay.run_once()

    publisher.fail = False
    result = relay.run_once()

    stored = outbox.messages[message.id]
    assert result.published == 1
    assert stored.published_at == NOW
    assert stored.attempts == 1  # conserva el historial del fallo
    assert publisher.published[0].event_id == message.id


@pytest.mark.parametrize(
    "corrupt",
    [
        lambda m: m.payload.pop("data"),
        lambda m: m.payload.update(event_version=99),
        lambda m: m.payload["data"].update(itinerary_id="no-es-un-uuid"),
    ],
    ids=["sin-data", "version-desconocida", "uuid-invalido"],
)
def test_mensaje_ilegible_se_marca_fallido_y_continua(corrupt):
    broken, valid = _message(minutes_ago=2), _message(minutes_ago=1)
    corrupt(broken)
    relay, outbox, publisher, _ = _relay([broken, valid])

    result = relay.run_once()

    assert result == RelayResult(published=1, failed=1)
    assert outbox.messages[broken.id].attempts == 1
    assert outbox.messages[broken.id].last_error.startswith("Mensaje ilegible")
    assert [e.event_id for e in publisher.published] == [valid.id]


def test_event_type_desconocido_se_marca_fallido_y_continua():
    unknown, valid = _message(minutes_ago=2), _message(minutes_ago=1)
    unknown.event_type = "itinerary.deleted"
    relay, outbox, publisher, _ = _relay([unknown, valid])

    result = relay.run_once()

    assert result == RelayResult(published=1, failed=1)
    assert "event_type desconocido" in outbox.messages[unknown.id].last_error
    assert [e.event_id for e in publisher.published] == [valid.id]


def test_error_inesperado_se_propaga_sin_commit():
    """Si falla la base de datos al marcar, no hay commit: el lote se reintentará entero."""

    class BrokenOutbox(FakeOutboxRepository):
        def mark_published(self, message_id, published_at):
            raise RuntimeError("PostgreSQL no disponible (simulado)")

    publisher = FakeEventPublisher()
    uow = FakeUnitOfWork()
    relay = OutboxRelay(BrokenOutbox([_message()]), publisher, uow, batch_size=10)

    with pytest.raises(RuntimeError):
        relay.run_once()

    assert uow.commits == 0
    assert len(publisher.published) == 1  # ya salió: se publicará de nuevo (duplicado)
