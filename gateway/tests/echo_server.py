"""Servidor eco: hace el papel de Airport Service e Itinerary Service en las pruebas del gateway.

Responde en JSON lo que recibió (servicio, método, ruta, headers y tamaño del cuerpo), para que
las pruebas comprueben qué le llegó al "servicio" a través del gateway. Rutas especiales:

- `.../slow`       → espera SLOW_RESPONSE_SECONDS antes de responder (para provocar el 504).
- `.../status-502` → responde un 502 propio "del servicio" (debe pasar por el gateway sin cambios).
- `.../redirect`   → responde 307 hacia /airports, como FastAPI con una barra final de más.

Cada respuesta trae además un X-Correlation-ID propio, como los servicios reales: el gateway debe
ocultarlo y dejar solo el suyo.

Usa solo la biblioteca estándar (http.server) y corre en un hilo dentro del proceso de pytest.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SLOW_RESPONSE_SECONDS = 3.0
SERVICE_CORRELATION_ID = "id-propio-del-servicio"
SERVICE_ERROR_CODE = "ERROR_DEL_SERVICIO"


class _EchoHTTPServer(ThreadingHTTPServer):
    """ThreadingHTTPServer que recuerda qué servicio simula."""

    # Hilos "daemon": una respuesta lenta pendiente no impide terminar pytest.
    daemon_threads = True

    def __init__(self, address: tuple[str, int], service_name: str) -> None:
        super().__init__(address, _EchoHandler)
        self.service_name = service_name


class _EchoHandler(BaseHTTPRequestHandler):
    server: _EchoHTTPServer

    def do_GET(self) -> None:
        self._respond()

    def do_POST(self) -> None:
        self._respond()

    def do_PUT(self) -> None:
        self._respond()

    def do_DELETE(self) -> None:
        self._respond()

    def _respond(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""

        if self.path.endswith("/redirect"):
            self._send(307, b"", {"Location": f"http://{self.headers['Host']}/airports"})
            return
        if self.path.endswith("/slow"):
            time.sleep(SLOW_RESPONSE_SECONDS)

        status = 502 if self.path.endswith("/status-502") else 200
        payload: dict[str, object] = {
            "service": self.server.service_name,
            "method": self.command,
            "path": self.path,
            # Nombres en minúsculas: los headers HTTP no distinguen mayúsculas.
            "headers": {name.lower(): value for name, value in self.headers.items()},
            "body_length": len(body),
        }
        if status == 502:
            payload["error"] = {"code": SERVICE_ERROR_CODE, "message": "Error generado por el servicio"}
        self._send(status, json.dumps(payload).encode(), {"Content-Type": "application/json"})

    def _send(self, status: int, body: bytes, headers: dict[str, str]) -> None:
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("X-Correlation-ID", SERVICE_CORRELATION_ID)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 (firma de la clase base)
        """Sin logs en consola: la salida de pytest queda limpia."""


class EchoServer:
    """Servidor eco en un puerto libre elegido por el sistema operativo."""

    def __init__(self, service_name: str, host: str) -> None:
        self._httpd = _EchoHTTPServer((host, 0), service_name)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return self._httpd.server_address[1]

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
