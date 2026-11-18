"""Fixtures de las pruebas de punta a punta (Fase 11).

Requieren el sistema completo levantado con el simulador de API Colombia:

    docker compose -f docker-compose.yml -f docker-compose.e2e.yml up -d --build

Las pruebas usan el sistema como lo usaría el frontend: por el API Gateway (puerto 8000). Para
comprobar lo que no se ve por HTTP (la outbox y el historial de notificaciones) leen las bases con
`docker compose exec ... psql`, como en las demostraciones. Si el gateway no responde, todas las
pruebas quedan SKIPPED.

Las pruebas crean datos en las bases REALES de Compose (es su propósito: probar el sistema tal cual)
y borran los itinerarios que crean. El historial de notificaciones se conserva, como en producción.
"""

import os
import subprocess
import time
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TypeVar
from uuid import uuid4

import httpx
import pytest

REPO_DIR = Path(__file__).resolve().parents[2]
GATEWAY_URL = os.environ.get("E2E_GATEWAY_URL", "http://localhost:8000")
JAEGER_URL = os.environ.get("E2E_JAEGER_URL", "http://localhost:16686")
PROMETHEUS_URL = os.environ.get("E2E_PROMETHEUS_URL", "http://localhost:9090")

# Tiempo máximo para procesos asíncronos: relay (cada 2 s), trigger, función y exportación de trazas
ASYNC_TIMEOUT_SECONDS = 60
POLL_SECONDS = 1.0

T = TypeVar("T")


def wait_for(check: Callable[[], T | None], description: str, timeout: float = ASYNC_TIMEOUT_SECONDS) -> T:
    """Repite `check` hasta que devuelva un valor (no None/False) o se agote el tiempo."""
    deadline = time.monotonic() + timeout
    while True:
        result = check()
        if result:
            return result
        if time.monotonic() > deadline:
            pytest.fail(f"No ocurrió a tiempo ({timeout} s): {description}")
        time.sleep(POLL_SECONDS)


def sql(service: str, user: str, database: str, query: str) -> list[list[str]]:
    """Ejecuta una consulta con psql dentro del contenedor de la base y devuelve las filas."""
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", service, "psql", "-U", user, "-d", database,
         "-tA", "-F", "|", "-c", query],
        cwd=REPO_DIR, capture_output=True, text=True, encoding="utf-8", timeout=30, check=True,
    )
    return [line.split("|") for line in result.stdout.splitlines() if line]


def itinerary_sql(query: str) -> list[list[str]]:
    return sql("itinerary-postgres", "itinerary", "itinerary_db", query)


def notification_sql(query: str) -> list[list[str]]:
    return sql("notification-postgres", "notification", "notification_db", query)


@pytest.fixture(scope="session")
def gateway() -> Iterator[httpx.Client]:
    """Cliente HTTP del API Gateway; SKIPPED si el sistema no está levantado."""
    try:
        httpx.get(f"{GATEWAY_URL}/health", timeout=3).raise_for_status()
    except httpx.HTTPError:
        pytest.skip(f"El API Gateway no responde en {GATEWAY_URL}: levanta el sistema con Docker Compose")
    with httpx.Client(base_url=GATEWAY_URL, timeout=20) as client:
        yield client


@pytest.fixture(scope="session")
def airport_ids(gateway: httpx.Client) -> tuple[int, int]:
    """Dos aeropuertos con ubicación conocida, tomados del catálogo (sirve con el simulador o la API real)."""
    response = gateway.get("/api/airports")
    assert response.status_code == 200, response.text
    located = [airport["id"] for airport in response.json() if airport["coordinates"] is not None]
    assert len(located) >= 2, "El catálogo necesita al menos dos aeropuertos con ubicación"
    return located[0], located[1]


@pytest.fixture
def correlation_id() -> str:
    return f"e2e-{uuid4()}"


@pytest.fixture
def itinerary_payload(airport_ids: tuple[int, int]) -> dict:
    travel_date = datetime.now(timezone(timedelta(hours=-5))) + timedelta(days=30)
    return {
        "traveler_name": "Ana Pérez (E2E)",
        "traveler_email": "ana.e2e@example.com",
        "departure_airport_id": airport_ids[0],
        "arrival_airport_id": airport_ids[1],
        "travel_date": travel_date.replace(microsecond=0).isoformat(),
        "duration_minutes": 75,
    }


@pytest.fixture
def created_ids(gateway: httpx.Client) -> Iterator[list[str]]:
    """Ids de itinerarios creados por la prueba; se borran al terminar (si la prueba no lo hizo)."""
    ids: list[str] = []
    yield ids
    for itinerary_id in ids:
        gateway.delete(f"/api/itineraries/{itinerary_id}")
