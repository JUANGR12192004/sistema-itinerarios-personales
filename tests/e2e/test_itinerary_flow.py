"""Recorrido de punta a punta de un itinerario (Fase 11).

Frontend (aquí, la prueba) → API Gateway → Itinerary Service → Airport Service → simulador de
API Colombia → PostgreSQL (itinerario + outbox, misma transacción) → Outbox Relay → RabbitMQ →
Event Trigger → SendNotificationFunction → notification_history.
"""

import httpx

from conftest import itinerary_sql, notification_sql, wait_for


def create(gateway: httpx.Client, payload: dict, correlation_id: str, created_ids: list[str]) -> dict:
    response = gateway.post("/api/itineraries", json=payload, headers={"X-Correlation-ID": correlation_id})
    assert response.status_code == 201, response.text
    body = response.json()
    created_ids.append(body["id"])
    return body


def notification_for(itinerary_id: str) -> list[str] | None:
    rows = notification_sql(
        "SELECT status, coalesce(recipient, ''), correlation_id, coalesce(status_reason, '') "
        f"FROM notification_history WHERE itinerary_id = '{itinerary_id}'"
    )
    return rows[0] if rows else None


def test_crear_un_itinerario_genera_una_notificacion_enviada(
    gateway: httpx.Client, itinerary_payload: dict, correlation_id: str, created_ids: list[str]
) -> None:
    itinerary = create(gateway, itinerary_payload, correlation_id, created_ids)

    # Transactional Outbox: el evento quedó registrado con el itinerario y el relay lo publica
    published = wait_for(
        lambda: itinerary_sql(
            "SELECT event_type FROM outbox_events "
            f"WHERE aggregate_id = '{itinerary['id']}' AND published_at IS NOT NULL"
        ),
        "el Outbox Relay publica el evento en RabbitMQ",
    )
    assert published == [["itinerary.created"]]

    # Event Trigger + función: una sola fila, enviada al correo, con el mismo correlation ID
    status, recipient, saved_correlation_id, _ = wait_for(
        lambda: notification_for(itinerary["id"]), "la función guarda la notificación"
    )
    assert (status, recipient, saved_correlation_id) == ("SENT", "ana.e2e@example.com", correlation_id)


def test_sin_correo_la_notificacion_queda_omitida(
    gateway: httpx.Client, itinerary_payload: dict, correlation_id: str, created_ids: list[str]
) -> None:
    itinerary = create(gateway, {**itinerary_payload, "traveler_email": None}, correlation_id, created_ids)

    status, recipient, _, reason = wait_for(
        lambda: notification_for(itinerary["id"]), "la función registra la notificación omitida"
    )
    assert (status, recipient) == ("SKIPPED", "")
    assert reason


def test_crud_completo_por_el_gateway(
    gateway: httpx.Client, itinerary_payload: dict, correlation_id: str, created_ids: list[str]
) -> None:
    itinerary = create(gateway, itinerary_payload, correlation_id, created_ids)
    url = f"/api/itineraries/{itinerary['id']}"

    assert gateway.get(url).json()["traveler_name"] == itinerary_payload["traveler_name"]
    assert itinerary["id"] in [item["id"] for item in gateway.get("/api/itineraries").json()]

    updated = gateway.put(url, json={**itinerary_payload, "duration_minutes": 90})
    assert updated.status_code == 200, updated.text
    assert updated.json()["duration_minutes"] == 90

    assert gateway.delete(url).status_code == 204
    missing = gateway.get(url, headers={"X-Correlation-ID": correlation_id})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "ITINERARY_NOT_FOUND"
    assert missing.json()["correlation_id"] == correlation_id


def test_un_aeropuerto_inexistente_se_rechaza_sin_guardar_nada(
    gateway: httpx.Client, itinerary_payload: dict
) -> None:
    before = itinerary_sql("SELECT count(*) FROM itineraries")

    response = gateway.post("/api/itineraries", json={**itinerary_payload, "arrival_airport_id": 9999})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "AIRPORT_NOT_FOUND"
    assert error["details"]["field"] == "arrival_airport_id"
    assert itinerary_sql("SELECT count(*) FROM itineraries") == before


def test_una_regla_de_negocio_se_rechaza_con_422(gateway: httpx.Client, itinerary_payload: dict) -> None:
    same_airport = {**itinerary_payload, "arrival_airport_id": itinerary_payload["departure_airport_id"]}

    response = gateway.post("/api/itineraries", json=same_airport)

    assert response.status_code == 422
    assert response.json()["error"]["code"] in {"INVALID_ITINERARY", "VALIDATION_ERROR"}
