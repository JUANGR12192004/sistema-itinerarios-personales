"""Genera y comprueba los requirements-lock.txt de las imágenes Docker.

¿Por qué existe? SonarCloud (regla S8544) exige que las imágenes instalen dependencias
"bloqueadas": no basta con fijar con == las dependencias directas, porque pip resolvería las
transitivas (starlette, anyio, grpcio...) de nuevo en cada build. Un archivo de bloqueo (lock)
lista TODAS las dependencias con versión exacta y el hash SHA-256 de sus archivos, y el
Dockerfile instala con "pip install --require-hashes": si algo no coincide, el build falla.

Uso (desde la raíz del repositorio, con Docker encendido e internet):

    python scripts/lock_requirements.py            regenera los cuatro locks
    python scripts/lock_requirements.py --check    comprueba que estén al día (sin Docker ni red)

Cómo genera cada lock:
1. Resuelve las dependencias con pip DENTRO de python:3.12-slim (la misma base de las imágenes),
   para x86_64 y aarch64 (Mac con Apple Silicon; con --platform, sin emular) y comprueba que den lo mismo.
   Resolver en Linux importa: algunas dependencias solo existen allí (por ejemplo uvloop).
2. Pide a PyPI los hashes de todos los wheels Linux (x86_64 y aarch64) de cada versión.

Solo usa la librería estándar de Python: no hay que instalar nada en el entorno virtual.
"""

import argparse
import json
import logging
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

logger = logging.getLogger("lock_requirements")

ROOT = Path(__file__).resolve().parent.parent
BASE_IMAGE = "python:3.12-slim"
PLATFORMS = ("linux/amd64", "linux/arm64")
# Arquitectura de cada plataforma Docker. python:3.12-slim (Debian) tiene glibc 2.36 o superior,
# así que acepta los wheels manylinux_2_X con X entre 17 y 36 (pip no amplía la etiqueta solo).
ARCHITECTURES = {"linux/amd64": "x86_64", "linux/arm64": "aarch64"}
LOCK_NAME = "requirements-lock.txt"

# Componente con imagen Docker → archivo con sus dependencias directas (fuente del lock)
TARGETS = {
    "services/airport-service": "requirements-runtime.txt",
    "services/itinerary-service": "requirements-runtime.txt",
    "serverless/event-trigger": "requirements-runtime.txt",
    "serverless/send-notification-function": "requirements-migrations.txt",
}

PIN_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?==([^\s;\\]+)")


def normalize(name: str) -> str:
    """Nombre canónico de un paquete (PEP 503): Python_JSON.logger → python-json-logger."""
    return re.sub(r"[-_.]+", "-", name).lower()


def read_pins(path: Path) -> dict[str, str]:
    """Lee las líneas 'paquete==versión' de un requirements, siguiendo los '-r otro.txt'."""
    pins: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("-r "):
            pins.update(read_pins(path.parent / line[3:].strip()))
            continue
        match = PIN_RE.match(line)
        if match:
            pins[normalize(match.group(1))] = match.group(2)
    return pins


def resolve(folder: Path, source: str, platform: str) -> dict[str, str]:
    """Resuelve todas las dependencias con pip dentro del contenedor (sin instalar nada).

    El contenedor siempre es el nativo del equipo. Para la otra arquitectura no se emula
    (con qemu tardaría ~10 minutos por componente): pip resuelve para esa plataforma con
    --platform, lo que comprueba que todas las dependencias publiquen wheels para ella.
    """
    arch = ARCHITECTURES[platform]
    platform_options = [option for glibc in range(17, 37) for option in ("--platform", f"manylinux_2_{glibc}_{arch}")]
    command = [
        "docker", "run", "--rm", "-v", f"{folder}:/src:ro", "-w", "/src", BASE_IMAGE,
        "pip", "install", "--dry-run", "--ignore-installed", "--quiet",
        "--disable-pip-version-check", "--only-binary", ":all:",
        *platform_options, "--python-version", "3.12", "--implementation", "cp",
        "--report", "-", "-r", source,
    ]
    output = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8").stdout
    report = json.loads(output)
    return {normalize(item["metadata"]["name"]): item["metadata"]["version"] for item in report["install"]}


def is_linux_cp312_wheel(filename: str) -> bool:
    """¿El wheel sirve en python:3.12-slim (glibc) para x86_64 o aarch64?"""
    python_tag, abi_tag, platform_tag = filename[:-len(".whl")].split("-")[-3:]
    platforms = platform_tag.split(".")
    linux = platform_tag == "any" or any(
        "manylinux" in tag and tag.endswith(("x86_64", "aarch64")) for tag in platforms
    )
    if not linux:
        return False
    pythons = set(python_tag.split("."))
    if abi_tag == "abi3":
        return any(re.fullmatch(r"cp3\d+", tag) and int(tag[3:]) <= 12 for tag in pythons)
    return abi_tag in ("none", "cp312") and bool(pythons & {"py3", "py2", "cp312", "py312"})


def wheel_hashes(name: str, version: str) -> list[str]:
    """Hashes SHA-256 publicados en PyPI para los wheels Linux de esa versión."""
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    with urllib.request.urlopen(url, timeout=30) as response:
        files = json.load(response)["urls"]
    hashes = sorted({
        file["digests"]["sha256"]
        for file in files
        if file["packagetype"] == "bdist_wheel" and is_linux_cp312_wheel(file["filename"])
    })
    if not hashes:
        raise SystemExit(f"{name}=={version} no publica wheels para Linux y Python 3.12")
    return hashes


def write_lock(folder: Path, source: str) -> None:
    resolved = {platform: resolve(folder, source, platform) for platform in PLATFORMS}
    pins = resolved[PLATFORMS[0]]
    if any(other != pins for other in resolved.values()):
        raise SystemExit(f"{folder.name}: amd64 y arm64 resuelven dependencias distintas: {resolved}")

    lines = [
        f"# Dependencias BLOQUEADAS de la imagen Docker, generadas a partir de {source}.",
        "# NO editar a mano: regenerar con  python scripts/lock_requirements.py  (desde la raíz).",
        "# Incluye las dependencias directas y las transitivas, cada una con versión exacta y los",
        "# hashes SHA-256 de sus wheels para Linux (x86_64 y aarch64, Python 3.12). El Dockerfile instala",
        "# con \"pip install --require-hashes\" (regla S8544 de SonarCloud).",
        "",
    ]
    for name in sorted(pins):
        hashes = wheel_hashes(name, pins[name])
        lines.append(f"{name}=={pins[name]} \\")
        for index, digest in enumerate(hashes):
            continuation = " \\" if index < len(hashes) - 1 else ""
            lines.append(f"    --hash=sha256:{digest}{continuation}")
    (folder / LOCK_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    logger.info("%s: %d paquetes bloqueados", folder.relative_to(ROOT).as_posix(), len(pins))


def check_lock(folder: Path, source: str) -> list[str]:
    """Compara las versiones directas con las del lock. Devuelve los problemas encontrados."""
    name = folder.relative_to(ROOT).as_posix()
    lock_path = folder / LOCK_NAME
    if not lock_path.exists():
        return [f"{name}: falta {LOCK_NAME}"]
    locked = read_pins(lock_path)
    problems = []
    for package, version in read_pins(folder / source).items():
        if locked.get(package) != version:
            problems.append(f"{name}: {source} pide {package}=={version}, el lock tiene {locked.get(package)}")
    return problems


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="solo comprobar que los locks estén al día")
    args = parser.parse_args()

    if args.check:
        problems = [p for folder, source in TARGETS.items() for p in check_lock(ROOT / folder, source)]
        for problem in problems:
            logger.error(problem)
        if problems:
            logger.error("Regenera los locks con: python scripts/lock_requirements.py")
            return 1
        logger.info("Los %d locks están al día.", len(TARGETS))
        return 0

    for folder, source in TARGETS.items():
        write_lock(ROOT / folder, source)
    return 0


if __name__ == "__main__":
    sys.exit(main())
