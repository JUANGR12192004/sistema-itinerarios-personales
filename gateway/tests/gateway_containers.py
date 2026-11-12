"""Funciones para construir la imagen del gateway y levantar contenedores de prueba con Docker.

Se usa el comando `docker` (subprocess) en lugar de una librería: no agrega dependencias y es
lo mismo que se escribe en la terminal.
"""

import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import httpx

GATEWAY_DIR = Path(__file__).resolve().parent.parent
TEST_IMAGE = "api-gateway:test"
CONTAINER_PREFIX = "api-gateway-test-"

# En Docker Desktop (macOS y Windows) host.docker.internal ya existe y apunta solo a una IPv4.
# En Linux (el CI) hay que agregarlo: "host-gateway" es la IP del equipo vista desde el contenedor.
# NO se agrega en Docker Desktop: allí "host-gateway" añade también una IPv6 que la red de Docker
# no puede alcanzar, y Nginx repartiría las solicitudes entre las dos (la mitad con 502).
HOST_ARGS = ["--add-host=host.docker.internal:host-gateway"] if sys.platform.startswith("linux") else []

DOCKER_TIMEOUT_SECONDS = 30
BUILD_TIMEOUT_SECONDS = 300  # la primera vez descarga la imagen de Nginx
STARTUP_TIMEOUT_SECONDS = 15
HEALTH_POLL_SECONDS = 0.2


class DockerUnavailableError(Exception):
    """Docker no está instalado o no está encendido."""


@dataclass(frozen=True)
class RunningGateway:
    """Contenedor del gateway en ejecución y la URL con la que se llega a él desde el equipo."""

    container_name: str
    base_url: str


def docker(*args: str, timeout: float = DOCKER_TIMEOUT_SECONDS) -> subprocess.CompletedProcess[str]:
    """Ejecuta `docker <args>` y devuelve el resultado sin lanzar error si falla."""
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=timeout, check=False
    )


def ensure_docker_available() -> None:
    try:
        result = docker("version", "--format", "{{.Server.Version}}", timeout=10)
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise DockerUnavailableError("Docker no está instalado o no responde") from error
    if result.returncode != 0:
        raise DockerUnavailableError("Docker no está encendido")


def build_test_image() -> str:
    """Construye la imagen desde gateway/ (el mismo Dockerfile y la misma plantilla de siempre)."""
    result = docker("build", "-q", "-t", TEST_IMAGE, str(GATEWAY_DIR), timeout=BUILD_TIMEOUT_SECONDS)
    if result.returncode != 0:
        raise RuntimeError(f"No se pudo construir la imagen del gateway:\n{result.stderr}")
    return TEST_IMAGE


def run_nginx_command(image: str, *nginx_args: str) -> subprocess.CompletedProcess[str]:
    """Ejecuta `nginx <args>` en un contenedor temporal (la imagen aplica la plantilla antes)."""
    return docker("run", "--rm", *HOST_ARGS, image, "nginx", *nginx_args)


def start_gateway(image: str, environment: dict[str, str]) -> RunningGateway:
    """Arranca un contenedor del gateway en un puerto libre de 127.0.0.1 y espera su /health."""
    name = f"{CONTAINER_PREFIX}{uuid4().hex[:8]}"
    env_args = [arg for key, value in environment.items() for arg in ("-e", f"{key}={value}")]
    # "127.0.0.1::8000": Docker elige un puerto libre del equipo, solo accesible desde el equipo.
    result = docker("run", "-d", "--name", name, "-p", "127.0.0.1::8000", *HOST_ARGS, *env_args, image)
    if result.returncode != 0:
        raise RuntimeError(f"No se pudo arrancar el gateway de prueba:\n{result.stderr}")

    port = docker("port", name, "8000/tcp").stdout.strip().splitlines()
    if not port:
        logs = docker("logs", name).stderr
        remove_gateway(name)
        raise RuntimeError(f"El gateway de prueba no publicó su puerto:\n{logs}")
    gateway = RunningGateway(container_name=name, base_url=f"http://{port[0]}")
    _wait_until_healthy(gateway)
    return gateway


def remove_gateway(container_name: str) -> None:
    docker("rm", "-f", container_name)


def _wait_until_healthy(gateway: RunningGateway) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{gateway.base_url}/health", timeout=1.0).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(HEALTH_POLL_SECONDS)
    logs = docker("logs", gateway.container_name).stderr
    remove_gateway(gateway.container_name)
    raise RuntimeError(f"El gateway de prueba no respondió /health a tiempo. Log:\n{logs}")
