"""Toma las capturas web de docs/evidencias con Playwright (Fase 12).

Herramienta de desarrollo: no es dependencia de ningún servicio. Se instala en su propio entorno
virtual (scripts/.venv) con scripts/requirements-evidencias.txt y `python -m playwright install chromium`.
Los pasos completos, para PowerShell, CMD y zsh, están en docs/evidencias/README.md.

Requisitos: el sistema levantado con Docker Compose (API Colombia real) y, antes, el paso `gateway`
de scripts/evidencias_terminal.py, que crea la traza que se abre en Jaeger, y el paso `dlq`, que deja
un mensaje en la DLQ. Los datos del CRUD son de ejemplo (nombre inventado y correo @example.com).

Uso, desde la raíz del repositorio:  python scripts/capturar_evidencias.py [swagger frontend jaeger rabbitmq grafana]
(sin argumentos, toma todas; con argumentos, solo las de esas páginas).
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "evidencias"

VIEWPORT = {"width": 1440, "height": 900}
TRAVELER = "María Rodríguez"
EMAIL = "maria@example.com"


def _shot(page: Page, name: str, full_page: bool = True) -> None:
    path = OUT / name
    page.screenshot(path=str(path), full_page=full_page)
    print(f"  {path.relative_to(ROOT)}")


def swagger(page: Page) -> None:
    for number, port, service in (("08", 8001, "airport"), ("09", 8002, "itinerary")):
        page.goto(f"http://localhost:{port}/docs")
        page.wait_for_selector(".swagger-ui .opblock", timeout=20_000)
        _shot(page, f"{number}-swagger-{service}.png")


def frontend(page: Page) -> None:
    page.goto("http://localhost:8000/")
    page.wait_for_selector("#section-airports .main-svg", timeout=30_000)
    page.wait_for_timeout(1500)  # termina de dibujar los puntos del mapa
    _shot(page, "10-frontend-mapa.png", full_page=False)

    # Crear: formulario lleno, antes de guardar
    page.click("#tab-itineraries")
    page.wait_for_selector("#traveler_name", timeout=20_000)
    travel = (datetime.now() + timedelta(days=40)).strftime("%Y-%m-%dT09:30")
    page.fill("#traveler_name", TRAVELER)
    page.fill("#traveler_email", EMAIL)
    page.select_option("#departure_airport_id", "1")
    page.select_option("#arrival_airport_id", "5")
    page.fill("#travel_date", travel)
    page.fill("#duration_minutes", "80")
    page.wait_for_timeout(1000)  # termina la animación de cambio de pestaña
    _shot(page, "11-frontend-crear.png")

    # Consultar: el itinerario guardado aparece en la tabla
    page.click("button[type=submit]")
    row = page.locator("table.itinerary-table tr", has_text=TRAVELER)
    row.wait_for(timeout=20_000)
    _shot(page, "12-frontend-consultar.png")

    # Actualizar: se edita la duración y se guarda
    row.get_by_role("button", name="Editar").click()
    page.wait_for_selector("text=Editar itinerario")
    page.fill("#duration_minutes", "95")
    page.click("button[type=submit]")
    page.locator("table.itinerary-table tr", has_text=TRAVELER).filter(has_text="95").wait_for(timeout=20_000)
    _shot(page, "13-frontend-actualizar.png")

    # Eliminar: se acepta la confirmación y la fila desaparece
    page.once("dialog", lambda dialog: dialog.accept())
    page.locator("table.itinerary-table tr", has_text=TRAVELER).get_by_role("button", name="Eliminar").click()
    # La lista se vuelve a cargar: se espera a que esté dibujada otra vez y ya sin la fila
    page.wait_for_function(
        "name => document.querySelector('.itinerary-count') && !document.body.innerText.includes(name)",
        arg=TRAVELER,
        timeout=20_000,
    )
    _shot(page, "14-frontend-eliminar.png")


def _session_trace_id() -> str:
    """Trace ID de la sesión, que fijó el paso gateway de scripts/evidencias_terminal.py."""
    text = (OUT / "03-gateway-correlation-id.txt").read_text(encoding="utf-8")
    match = re.search(r"^Trace ID de la sesión: ([0-9a-f]{32})$", text, flags=re.MULTILINE)
    if not match:
        raise SystemExit("Primero hay que generar la evidencia 03: python scripts/evidencias_terminal.py gateway")
    return match.group(1)


def jaeger(page: Page) -> None:
    page.goto(f"http://localhost:16686/trace/{_session_trace_id()}")
    page.wait_for_selector("text=send-notification-function", timeout=30_000)
    page.wait_for_timeout(1000)
    _shot(page, "15-jaeger-traza.png")


def grafana(page: Page) -> None:
    # Usuario y clave de desarrollo de Grafana (.env.example de la raíz)
    page.goto("http://localhost:3000/login")
    page.fill("input[name=user]", "admin")
    page.fill("input[name=password]", "admin")
    page.click("button[type=submit]")
    skip = page.get_by_role("button", name="Skip")  # Grafana sugiere cambiar la clave por defecto
    try:
        skip.click(timeout=5_000)
    except PlaywrightTimeoutError:  # si Grafana no muestra la sugerencia, se sigue
        pass
    page.goto("http://localhost:3000/d/sistema-itinerarios-v1/?orgId=1&from=now-30m&to=now&kiosk")
    page.wait_for_selector("text=Itinerarios creados", timeout=30_000)
    page.wait_for_timeout(6000)  # los paneles consultan Prometheus
    _shot(page, "16-grafana-dashboard.png")


def rabbitmq(page: Page) -> None:
    page.goto("http://localhost:15672/")
    page.fill("input[name=username]", "guest")
    page.fill("input[name=password]", "guest")
    page.click("input[type=submit]")
    page.wait_for_selector("#main", timeout=20_000)
    # La cabecera del panel es fija (position: fixed): en una captura de página completa se
    # repetiría en medio de la imagen. Se deja estática solo para la captura.
    page.add_style_tag(content="#header { position: static !important; }")
    page.goto("http://localhost:15672/#/queues")
    page.wait_for_selector("text=notification.itinerary-created.dlq", timeout=20_000)
    page.wait_for_timeout(1500)
    _shot(page, "17-rabbitmq-colas.png")

    # Un mensaje de la DLQ, leído sin sacarlo de la cola (Nack message requeue true)
    page.goto("http://localhost:15672/#/queues/%2F/notification.itinerary-created.dlq")
    page.wait_for_selector("text=Get messages", timeout=20_000)
    header = page.locator("h2", has_text="Get messages")
    if "section-hidden" in (header.locator("..").get_attribute("class") or ""):
        header.click()
    page.select_option("select[name=ackmode]", "ack_requeue_true")
    page.click("input[value='Get Message(s)']")
    message = page.locator("#msg-wrapper", has_text="Message 1")
    message.wait_for(timeout=20_000)
    _shot(page, "18-rabbitmq-dlq-mensaje.png")


def main() -> None:
    sections = {"swagger": swagger, "frontend": frontend, "jaeger": jaeger, "rabbitmq": rabbitmq, "grafana": grafana}
    selected = sys.argv[1:] or list(sections)
    unknown = [name for name in selected if name not in sections]
    if unknown:
        sys.exit(f"Páginas desconocidas: {unknown}. Disponibles: {', '.join(sections)}")
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport=VIEWPORT, locale="es-CO", timezone_id="America/Bogota")
        page = context.new_page()
        for name in selected:
            sections[name](page)
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
