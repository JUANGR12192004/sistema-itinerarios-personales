"""Observabilidad de punta a punta (Fase 11): una sola traza recorre todo el sistema.

El cliente envía un `traceparent` (W3C Trace Context) con un trace_id conocido. El gateway lo
continúa (ADR-036) y cada componente lo propaga: HTTP hasta Airport Service, la outbox y los
headers AMQP hasta el trigger, y el cuerpo del evento hasta la función (ADR-037). Después se
pide a Jaeger esa traza por su id y se comprueba qué servicios aparecen en ella.
"""

import secrets

import httpx

from conftest import JAEGER_URL, PROMETHEUS_URL, wait_for

EXPECTED_SERVICES = {
    "api-gateway",
    "itinerary-service",
    "airport-service",
    "itinerary-service-relay",
    "event-trigger",
    "send-notification-function",
}


def services_in_trace(trace_id: str) -> set[str] | None:
    response = httpx.get(f"{JAEGER_URL}/api/traces/{trace_id}", timeout=5)
    if response.status_code != 200 or not response.json().get("data"):
        return None
    trace = response.json()["data"][0]
    services = {process["serviceName"] for process in trace["processes"].values()}
    return services if EXPECTED_SERVICES <= services else None


def test_una_traza_recorre_todo_el_sistema(
    gateway: httpx.Client, itinerary_payload: dict, created_ids: list[str]
) -> None:
    trace_id = secrets.token_hex(16)
    traceparent = f"00-{trace_id}-{secrets.token_hex(8)}-01"

    response = gateway.post("/api/itineraries", json=itinerary_payload, headers={"traceparent": traceparent})
    assert response.status_code == 201, response.text
    created_ids.append(response.json()["id"])

    services = wait_for(lambda: services_in_trace(trace_id), f"Jaeger muestra la traza {trace_id} completa")
    assert EXPECTED_SERVICES <= services


def test_prometheus_recoge_las_metricas_de_todos_los_componentes(gateway: httpx.Client) -> None:
    def targets_up() -> list[dict] | None:
        targets = httpx.get(f"{PROMETHEUS_URL}/api/v1/targets", timeout=5).json()["data"]["activeTargets"]
        return targets if targets and all(target["health"] == "up" for target in targets) else None

    targets = wait_for(targets_up, "todos los destinos de Prometheus están arriba")
    assert len(targets) >= 4  # Airport, Itinerary, relay y trigger (ADR-038)


def test_crear_un_itinerario_incrementa_la_metrica_de_negocio(
    gateway: httpx.Client, itinerary_payload: dict, created_ids: list[str]
) -> None:
    def created_total() -> float:
        query = httpx.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": "sum(itineraries_created_total)"}, timeout=5)
        result = query.json()["data"]["result"]
        return float(result[0]["value"][1]) if result else 0.0

    before = created_total()
    response = gateway.post("/api/itineraries", json=itinerary_payload)
    assert response.status_code == 201, response.text
    created_ids.append(response.json()["id"])

    wait_for(lambda: created_total() >= before + 1, "Prometheus ve el nuevo itinerario creado")
