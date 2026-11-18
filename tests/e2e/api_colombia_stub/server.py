"""Simulador de API Colombia para las pruebas de punta a punta (Fase 11).

Reemplaza a https://api-colombia.com/api/v1 solo en docker-compose.e2e.yml. Así las pruebas E2E
no dependen de internet ni de un proveedor externo, igual que respx en las pruebas unitarias del
Adapter, pero a nivel de sistema. Responde como el proveedor real (CLAUDE.md 8.3):

- GET /api/v1/Airport        → 200 con la lista de airports.json
- GET /api/v1/Airport/{id}   → 200 con el aeropuerto, 404 con cuerpo vacío si no existe,
                               400 con cuerpo vacío si el id es 0 o no es un número
- GET /health                → 200 (healthcheck de Docker Compose)

Los datos conservan los defectos reales: coordenadas intercambiadas, códigos "N/A" y el id 43 con 0, 0.
Solo usa la librería estándar.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8080
PREFIX = "/api/v1/Airport"
AIRPORTS = json.loads((Path(__file__).parent / "airports.json").read_text(encoding="utf-8"))
BY_ID = {airport["id"]: airport for airport in AIRPORTS}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0].rstrip("/")
        if path == "/health":
            self._send(200, {"status": "ok"})
        elif path == PREFIX:
            self._send(200, AIRPORTS)
        elif path.startswith(PREFIX + "/"):
            self._airport(path.removeprefix(PREFIX + "/"))
        else:
            self._send(404, None)

    def _airport(self, raw_id: str) -> None:
        if not raw_id.isdigit() or int(raw_id) == 0:
            self._send(400, None)
        elif int(raw_id) in BY_ID:
            self._send(200, BY_ID[int(raw_id)])
        else:
            self._send(404, None)

    def _send(self, status: int, body: object) -> None:
        content = b"" if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        if content:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 (firma de la clase base)
        """Sin log por solicitud: el simulador no es parte del sistema observado."""


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()  # noqa: S104 (red interna de Compose)
