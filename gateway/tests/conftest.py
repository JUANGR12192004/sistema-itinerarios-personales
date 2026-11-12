"""Fixtures de las pruebas del API Gateway.

AISLAMIENTO: estas pruebas NO usan el gateway real (puerto 8000) ni los servicios reales.
Levantan sus propios contenedores del gateway (la misma imagen y la misma plantilla, etiqueta
`api-gateway:test`) que apuntan a servidores eco de Python. Así:

- no crean, cambian ni borran datos reales;
- no consumen el límite de solicitudes del gateway que se usa en una demostración;
- pueden provocar fallos (servicio apagado, servicio lento) sin apagar nada real.

Los contenedores se borran al terminar. Sin Docker, todas estas pruebas quedan SKIPPED.
Las pruebas "smoke" contra el gateway real están en test_real_gateway.py, con su propio fixture.

gateway_image            — imagen construida desde gateway/ (SKIPPED sin Docker).
gateway                  — gateway con los dos servicios simulados por ecos y un timeout de lectura
                           corto (para el 504). Su ráfaga es enorme, para que el rate limiting no
                           interfiera en las demás pruebas: el límite real se prueba aparte.
gateway_without_services — gateway cuyos servicios no existen (puertos cerrados): 502.
rate_limited_gateway     — gateway nuevo para cada prueba, con el límite real (10 r/s, ráfaga 20).
"""

import os
import socket
import sys
from collections.abc import Callable, Iterator

import httpx
import pytest

from tests.echo_server import EchoServer
from tests.gateway_containers import (
    DockerUnavailableError,
    RunningGateway,
    build_test_image,
    ensure_docker_available,
    remove_gateway,
    start_gateway,
)

HTTP_TIMEOUT_SECONDS = 5.0
# Menor que SLOW_RESPONSE_SECONDS del eco (3 s): la ruta /slow provoca el 504.
TEST_READ_TIMEOUT = "1s"

# Dirección en la que escuchan los ecos. En Docker Desktop (macOS y Windows) el contenedor llega
# a 127.0.0.1 del equipo por host.docker.internal. En Linux (el CI), host.docker.internal es la IP
# del puente de Docker, así que el eco debe escuchar en todas las interfaces. Se puede cambiar con
# la variable GATEWAY_TEST_ECHO_HOST.
ECHO_HOST = os.environ.get("GATEWAY_TEST_ECHO_HOST") or (
    "0.0.0.0" if sys.platform.startswith("linux") else "127.0.0.1"  # noqa: S104 (solo pruebas)
)


def _closed_port() -> int:
    """Un puerto en el que no escucha nadie: simula un servicio apagado."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def gateway_image() -> str:
    try:
        ensure_docker_available()
    except DockerUnavailableError as error:
        pytest.skip(f"{error} — omitiendo pruebas del gateway")
    return build_test_image()


@pytest.fixture(scope="session")
def airport_echo() -> Iterator[EchoServer]:
    server = EchoServer("airport-echo", ECHO_HOST)
    server.start()
    yield server
    server.stop()


@pytest.fixture(scope="session")
def itinerary_echo() -> Iterator[EchoServer]:
    server = EchoServer("itinerary-echo", ECHO_HOST)
    server.start()
    yield server
    server.stop()


@pytest.fixture(scope="session")
def gateway(
    gateway_image: str, airport_echo: EchoServer, itinerary_echo: EchoServer
) -> Iterator[RunningGateway]:
    running = start_gateway(
        gateway_image,
        {
            "AIRPORT_SERVICE_UPSTREAM": f"host.docker.internal:{airport_echo.port}",
            "ITINERARY_SERVICE_UPSTREAM": f"host.docker.internal:{itinerary_echo.port}",
            "GATEWAY_PROXY_READ_TIMEOUT": TEST_READ_TIMEOUT,
            "GATEWAY_RATE_BURST": "1000",
        },
    )
    yield running
    remove_gateway(running.container_name)


@pytest.fixture(scope="session")
def gateway_without_services(gateway_image: str) -> Iterator[RunningGateway]:
    running = start_gateway(
        gateway_image,
        {
            "AIRPORT_SERVICE_UPSTREAM": f"host.docker.internal:{_closed_port()}",
            "ITINERARY_SERVICE_UPSTREAM": f"host.docker.internal:{_closed_port()}",
        },
    )
    yield running
    remove_gateway(running.container_name)


@pytest.fixture
def rate_limited_gateway(gateway_image: str) -> Iterator[RunningGateway]:
    """Contenedor nuevo en cada prueba: su contador de solicitudes empieza vacío.

    Los servicios no existen (502): el rate limiting se aplica ANTES de llamar al servicio,
    así que no hace falta que exista para comprobarlo.
    """
    running = start_gateway(
        gateway_image,
        {
            "AIRPORT_SERVICE_UPSTREAM": f"host.docker.internal:{_closed_port()}",
            "ITINERARY_SERVICE_UPSTREAM": f"host.docker.internal:{_closed_port()}",
        },
    )
    yield running
    remove_gateway(running.container_name)


def _client(running: RunningGateway) -> httpx.Client:
    return httpx.Client(base_url=running.base_url, timeout=HTTP_TIMEOUT_SECONDS)


@pytest.fixture
def client(gateway: RunningGateway) -> Iterator[httpx.Client]:
    with _client(gateway) as http_client:
        yield http_client


@pytest.fixture
def client_without_services(gateway_without_services: RunningGateway) -> Iterator[httpx.Client]:
    with _client(gateway_without_services) as http_client:
        yield http_client


@pytest.fixture
def rate_limited_client(rate_limited_gateway: RunningGateway) -> Iterator[httpx.Client]:
    with _client(rate_limited_gateway) as http_client:
        yield http_client


@pytest.fixture
def assert_gateway_error() -> Callable[[httpx.Response, int, str], dict]:
    """Comprueba que la respuesta es un error del gateway con el formato de la sección 10.2."""

    def check(response: httpx.Response, status: int, code: str) -> dict:
        assert response.status_code == status
        assert response.headers["content-type"].startswith("application/json")
        body = response.json()
        assert set(body) == {"error", "correlation_id"}
        assert set(body["error"]) == {"code", "message", "details"}
        assert body["error"]["code"] == code
        assert body["error"]["message"]
        # El mismo correlation ID en el cuerpo y en el header (un solo header).
        assert response.headers.get_list("x-correlation-id") == [body["correlation_id"]]
        return body

    return check
