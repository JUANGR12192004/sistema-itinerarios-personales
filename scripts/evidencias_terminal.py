"""Genera las evidencias de terminal de docs/evidencias (Fase 12).

Cada paso ejecuta comandos reales contra el sistema levantado con Docker Compose y guarda su
salida en un archivo .txt con la fecha, el equipo y el comando que la produjo. Solo usa la
librería estándar de Python, `docker compose` y `curl` (en Windows 10/11, `curl` es curl.exe).

Uso, desde la raíz del repositorio (igual en PowerShell, CMD y zsh):

    python scripts/evidencias_terminal.py pruebas      # requiere el simulador (ver docs/evidencias/README.md)
    python scripts/evidencias_terminal.py estado gateway notificacion outbox rate-limit dlq

Los datos de las solicitudes son de ejemplo (nombres inventados y correos @example.com).
"""

from __future__ import annotations

import json
import platform
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "evidencias"
GATEWAY = "http://localhost:8000"
RABBITMQ_API = "http://localhost:15672/api"

# Identificadores únicos por sesión (fecha y hora), para no mezclarse con datos de sesiones
# anteriores. Los pasos que necesitan los de otro paso los leen de la evidencia 03.
SESSION = datetime.now().strftime("%Y%m%d%H%M%S")
CORRELATION_ID = f"evidencia-{SESSION}"
OUTBOX_CORRELATION_ID = f"evidencia-outbox-{SESSION}"
TRACE_ID = f"12c{SESSION}".ljust(32, "0")  # 32 dígitos hexadecimales
TRACEPARENT = f"00-{TRACE_ID}-12c0e0de0c0de012-01"


# --- utilidades ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def _future_date(days: int) -> str:
    """Fecha de viaje futura con la zona horaria de Colombia (ADR-017)."""
    bogota = timezone(timedelta(hours=-5))
    when = (datetime.now(bogota) + timedelta(days=days)).replace(hour=8, minute=0, second=0, microsecond=0)
    return when.isoformat()


def _run(args: list[str], check: bool = False) -> str:
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and result.returncode != 0:
        raise RuntimeError(f"Falló: {' '.join(args)}\n{result.stdout}\n{result.stderr}")
    return (result.stdout + result.stderr).rstrip()


def _show(args: list[str]) -> str:
    """Muestra el comando como se escribiría en zsh (en PowerShell y CMD, curl.exe y comillas dobles)."""
    def quote(arg: str) -> str:
        if "'" in arg and '"' not in arg and "$" not in arg:
            return f'"{arg}"'  # SQL con comillas simples: más legible entre comillas dobles
        return shlex.quote(arg)

    return "$ " + " ".join(quote(a) for a in args)


def _psql(service: str, user: str, db: str, sql: str) -> tuple[list[str], str]:
    args = ["docker", "compose", "exec", "-T", service, "psql", "-U", user, "-d", db, "-c", sql]
    return args, _run(args)


def _psql_value(service: str, user: str, db: str, sql: str) -> str:
    """Un solo valor, sin formato de tabla (para esperar condiciones)."""
    return _run(["docker", "compose", "exec", "-T", service, "psql", "-U", user, "-d", db, "-Atc", sql]).strip()


def _logs(service: str, since: str, contains: tuple[str, ...]) -> list[str]:
    """Líneas de log JSON del servicio, resumidas a hora, nivel y mensaje."""
    raw = _run(["docker", "compose", "logs", "--no-log-prefix", "--since", since, service])
    lines = []
    for line in raw.splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = str(entry.get("message", ""))
        if any(text in message for text in contains):
            lines.append(f"{entry.get('timestamp', '')} {entry.get('level', '')} {message[:220]}")
    return lines


def _wait(description: str, condition, timeout: float = 90.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(2)
    print(f"  Aviso: no se cumplió a tiempo: {description}")
    return False


def _write(number: str, name: str, title: str, step: str, blocks: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    header = [
        f"Evidencia {number} — {title}",
        f"Fecha: {_now()}",
        f"Equipo: {platform.system()} ({platform.machine()}), {_run(['docker', '--version'])}",
        f"Generada con: python scripts/evidencias_terminal.py {step}",
        "",
        "",
    ]
    path = OUT / name
    path.write_text("\n".join(header) + "\n\n".join(blocks).rstrip() + "\n", encoding="utf-8")
    print(f"  {path.relative_to(ROOT)}")


def _from_evidence_03(prefix: str) -> str:
    """Lee de la evidencia 03 el valor de una línea "prefijo: valor" (correlation ID de la sesión)."""
    text = (OUT / "03-gateway-correlation-id.txt").read_text(encoding="utf-8")
    match = re.search(rf"^{re.escape(prefix)}: (\S+)$", text, flags=re.MULTILINE)
    if not match:
        raise RuntimeError("Primero hay que generar la evidencia 03 (paso gateway)")
    return match.group(1)


def _itinerary(name: str, email: str, days: int, duration: int) -> str:
    return json.dumps(
        {
            "traveler_name": name,
            "traveler_email": email,
            "departure_airport_id": 1,
            "arrival_airport_id": 5,
            "travel_date": _future_date(days),
            "duration_minutes": duration,
        },
        ensure_ascii=False,
    )


# --- pasos ---------------------------------------------------------------------------------

SUITES = [
    "libs/observability",
    "services/airport-service",
    "services/itinerary-service",
    "serverless/send-notification-function",
    "serverless/event-trigger",
    "gateway",
    "tests/e2e",
]


def step_pruebas() -> None:
    """01: las siete suites con el sistema y el simulador de API Colombia encendidos."""
    blocks = [
        "Precondición: docker compose -f docker-compose.yml -f docker-compose.e2e.yml up -d --wait\n"
        "(el simulador de API Colombia solo hace falta para tests/e2e). Cada suite se ejecuta desde su carpeta\n"
        "con el Python de su entorno virtual (.venv)."
    ]
    total = 0
    for suite in SUITES:
        folder = ROOT / suite
        python = folder / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        args = [str(python), "-m", "pytest", "-q", "-p", "no:cacheprovider"]
        result = subprocess.run(args, cwd=folder, capture_output=True, text=True, encoding="utf-8", errors="replace")
        last = (result.stdout.strip().splitlines() or ["(sin salida)"])[-1]
        total += int(last.split(" passed")[0].split()[-1]) if " passed" in last else 0
        blocks.append(f"$ cd {suite} && .venv/bin/python -m pytest -q\n{last}   (código de salida {result.returncode})")
    blocks.append(f"Total: {total} pruebas pasan.")
    _write("01", "01-pruebas.txt", "Las siete suites de pruebas", "pruebas", blocks)


def step_estado() -> None:
    """02: todos los contenedores sanos."""
    args = ["docker", "compose", "ps", "-a", "--format", "table {{.Service}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"]
    _write("02", "02-docker-compose-ps.txt", "docker compose ps con todo el sistema sano", "estado",
           [_show(args) + "\n" + _run(args)])


def step_gateway() -> None:
    """03: el gateway reenvía el X-Correlation-ID (y un traceparent conocido) o genera uno."""
    body = _itinerary("Ana Pérez", "ana@example.com", 30, 75)
    post = ["curl", "-s", "-i", "-X", "POST", f"{GATEWAY}/api/itineraries",
            "-H", "Content-Type: application/json",
            "-H", f"X-Correlation-ID: {CORRELATION_ID}",
            "-H", f"traceparent: {TRACEPARENT}",
            "-d", body]
    get = ["curl", "-s", "-i", f"{GATEWAY}/api/itineraries"]
    blocks = [
        f"Correlation ID de la sesión: {CORRELATION_ID}\nTrace ID de la sesión: {TRACE_ID}",
        "1) POST con X-Correlation-ID: el gateway lo reenvía y vuelve en la respuesta. El traceparent fija el\n"
        "   trace ID de la sesión para abrir la traza en Jaeger (evidencia 15).\n" + _show(post) + "\n" + _run(post),
        "2) GET sin X-Correlation-ID: el gateway genera uno con forma de UUID.\n" + _show(get) + "\n" + _run(get),
    ]
    _write("03", "03-gateway-correlation-id.txt", "Respuesta del gateway con X-Correlation-ID", "gateway", blocks)


def step_notificacion() -> None:
    """05: el evento del itinerario de la evidencia 03 terminó en notification_history como SENT."""
    correlation_id = _from_evidence_03("Correlation ID de la sesión")
    sql = ("SELECT event_id, itinerary_id, recipient, channel, status, correlation_id, processed_at "
           f"FROM notification_history WHERE correlation_id = '{correlation_id}';")
    _wait("registro en notification_history",
          lambda: "SENT" in _psql("notification-postgres", "notification", "notification_db", sql)[1])
    args, out = _psql("notification-postgres", "notification", "notification_db", sql)
    event_id = _psql_value("notification-postgres", "notification", "notification_db",
                           f"SELECT event_id FROM notification_history WHERE correlation_id = '{correlation_id}';")
    itinerary_id = _psql_value("notification-postgres", "notification", "notification_db",
                               f"SELECT itinerary_id FROM notification_history WHERE correlation_id = '{correlation_id}';")
    outbox_sql = ("SELECT id AS event_id, event_type, published_at, attempts FROM outbox_events "
                  f"WHERE payload->>'correlation_id' = '{correlation_id}';")
    args2, out2 = _psql("itinerary-postgres", "itinerary", "itinerary_db", outbox_sql)
    blocks = [
        f"Itinerario creado en la evidencia 03 (X-Correlation-ID: {correlation_id}).",
        "1) El evento en la outbox de Itinerary Service, ya publicado por el Outbox Relay:\n" + _show(args2) + "\n" + out2,
        "2) La notificación en el historial de SendNotificationFunction (otra base de datos), con el mismo\n"
        "   event_id y el mismo correlation_id que llegó al gateway:\n" + _show(args) + "\n" + out,
        "3) Log de la función:\n" + "\n".join(
            _logs("send-notification-function", "30m", (event_id, itinerary_id)) or ["(sin líneas)"]),
    ]
    _write("05", "05-notification-history.txt", "Registro SENT en notification_history", "notificacion", blocks)


def step_outbox() -> None:
    """06: Transactional Outbox con RabbitMQ detenido: el evento espera y se publica al volver."""
    sql = ("SELECT id AS event_id, published_at, attempts, left(last_error, 70) AS last_error FROM outbox_events "
           f"WHERE payload->>'correlation_id' = '{OUTBOX_CORRELATION_ID}';")
    blocks = []

    stop = ["docker", "compose", "stop", "rabbitmq"]
    blocks.append("1) Se detiene RabbitMQ.\n" + _show(stop) + "\n" + _run(stop, check=True))

    body = _itinerary("Luis Gómez", "luis@example.com", 45, 90)
    post = ["curl", "-s", "-w", "\\nHTTP %{http_code}\\n", "-X", "POST", f"{GATEWAY}/api/itineraries",
            "-H", "Content-Type: application/json", "-H", f"X-Correlation-ID: {OUTBOX_CORRELATION_ID}", "-d", body]
    blocks.append("2) Se crea un itinerario: la API responde 201 aunque RabbitMQ esté caído, porque solo escribe en\n"
                  "   PostgreSQL (itinerario + evento en la misma transacción).\n" + _show(post) + "\n" + _run(post))

    time.sleep(10)
    args, out = _psql("itinerary-postgres", "itinerary", "itinerary_db", sql)
    blocks.append("3) Diez segundos después el evento sigue PENDIENTE (published_at vacío) y el relay suma intentos:\n"
                  + _show(args) + "\n" + out)
    relay = _logs("outbox-relay", "30s", ("No se pudo publicar", "Ciclo del Outbox Relay"))[-4:]
    blocks.append("4) Log del Outbox Relay mientras RabbitMQ está caído (últimas líneas):\n"
                  + "\n".join(relay or ["(sin líneas de error)"]))

    start = ["docker", "compose", "up", "-d", "--wait", "rabbitmq"]
    blocks.append("5) Se vuelve a levantar RabbitMQ.\n" + _show(start) + "\n" + _run(start, check=True))

    published = ("SELECT published_at IS NOT NULL FROM outbox_events "
                 f"WHERE payload->>'correlation_id' = '{OUTBOX_CORRELATION_ID}';")
    _wait("evento publicado", lambda: _psql_value("itinerary-postgres", "itinerary", "itinerary_db", published) == "t")
    args, out = _psql("itinerary-postgres", "itinerary", "itinerary_db", sql)
    blocks.append("6) El relay publica el evento en cuanto RabbitMQ vuelve (published_at con fecha):\n"
                  + _show(args) + "\n" + out)

    hist = ("SELECT event_id, recipient, status, correlation_id FROM notification_history "
            f"WHERE correlation_id = '{OUTBOX_CORRELATION_ID}';")
    _wait("notificación", lambda: "SENT" in _psql("notification-postgres", "notification", "notification_db", hist)[1])
    args, out = _psql("notification-postgres", "notification", "notification_db", hist)
    blocks.append("7) Y la notificación llega al historial: no se perdió ningún evento.\n" + _show(args) + "\n" + out)
    _write("06", "06-outbox-rabbitmq-detenido.txt",
           "Transactional Outbox: RabbitMQ detenido, evento pendiente y publicado al volver", "outbox", blocks)


def step_rate_limit() -> None:
    """04: 429 RATE_LIMIT_EXCEEDED al superar 10 solicitudes/s (+20 de ráfaga)."""
    statuses: list[int] = []
    first_429 = ""
    for _ in range(40):
        try:
            with urllib.request.urlopen(f"{GATEWAY}/api/itineraries", timeout=5) as response:
                statuses.append(response.status)
        except urllib.error.HTTPError as error:
            statuses.append(error.code)
            if error.code == 429 and not first_429:
                headers = "\n".join(f"{k}: {v}" for k, v in error.headers.items())
                first_429 = f"HTTP/1.1 {error.code}\n{headers}\n\n{error.read().decode('utf-8')}"
    summary = ", ".join(f"{code} × {statuses.count(code)}" for code in sorted(set(statuses)))
    blocks = [
        "40 solicitudes GET /api/itineraries seguidas desde la misma IP (urllib de Python, una tras otra).",
        f"Códigos en orden: {' '.join(str(s) for s in statuses)}",
        f"Resumen: {summary}",
        "Primera respuesta 429 completa:\n" + (first_429 or "(no hubo 429)"),
    ]
    _write("04", "04-rate-limit-429.txt", "429 del rate limiting del gateway", "rate-limit", blocks)
    time.sleep(3)  # deja que el límite se recupere antes del siguiente paso


def step_dlq() -> None:
    """07: un evento que no cumple el contrato va a la DLQ sin reintentos."""
    publish = ["curl", "-s", "-u", "guest:guest", "-X", "POST",
               f"{RABBITMQ_API}/exchanges/%2F/itinerary.events/publish",
               "-H", "Content-Type: application/json",
               "--data-binary", "@serverless/event-trigger/demo/publish-invalid-event.json"]
    blocks = ["1) Se publica a mano un evento inválido (Itinerary Service solo produce eventos válidos):\n"
              + _show(publish) + "\n" + _run(publish)]
    time.sleep(6)
    blocks.append("2) Log del Event Trigger:\n" + "\n".join(
        _logs("event-trigger", "1m", ("DLQ", "rechaz")) or ["(sin líneas)"]))
    lines = []
    for queue in ("notification.itinerary-created", "notification.itinerary-created.dlq"):
        args = ["curl", "-s", "-u", "guest:guest", f"{RABBITMQ_API}/queues/%2F/{queue}"]
        data = json.loads(_run(args))
        lines.append(f"{queue}: {data.get('messages')} mensajes ({data.get('consumers')} consumidores)")
    blocks.append("3) Mensajes en cada cola (API del panel de RabbitMQ):\n" + "\n".join(lines))
    _write("07", "07-dlq-evento-invalido.txt", "Evento inválido enviado a la DLQ", "dlq", blocks)


STEPS = {
    "pruebas": step_pruebas,
    "estado": step_estado,
    "gateway": step_gateway,
    "notificacion": step_notificacion,
    "outbox": step_outbox,
    "rate-limit": step_rate_limit,
    "dlq": step_dlq,
}

if __name__ == "__main__":
    names = sys.argv[1:] or ["estado", "gateway", "notificacion", "outbox", "rate-limit", "dlq"]
    unknown = [n for n in names if n not in STEPS]
    if unknown:
        sys.exit(f"Pasos desconocidos: {unknown}. Disponibles: {', '.join(STEPS)}")
    for name in names:
        print(f"Paso {name}")
        STEPS[name]()
