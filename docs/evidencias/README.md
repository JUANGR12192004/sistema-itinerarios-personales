# Evidencias

Capturas y salidas de terminal que muestran el sistema funcionando. Las evidencias 02 a 18 se obtuvieron el
**2026-11-18 en una sola sesión** (macOS con Apple Silicon, Docker Desktop 29.9.3), con el sistema levantado con
Docker Compose y la **API Colombia real**. La evidencia 01 se **regeneró el 2026-11-19** en el mismo equipo, después de
las correcciones posteriores a la Fase 12 (PR #32 y #33), para que sus totales coincidan con el README; sus pruebas E2E
usan el simulador. Todos los datos son de ejemplo: nombres inventados y correos `@example.com`.

Las evidencias 19 y 20 las tomó el equipo desde su cuenta de SonarCloud y de GitHub. No queda ninguna evidencia
pendiente.

## Lista

| N.º | Archivo | Qué debe verse | Cómo se obtuvo |
|---|---|---|---|
| 01 | [`01-pruebas.txt`](01-pruebas.txt) | Las siete suites pasan: libs/observability 19, Airport 199, Itinerary 200, función 70, Event Trigger 87, gateway 53 y E2E 14. Total **642**, código de salida 0 en todas (2026-11-19) | `evidencias_terminal.py pruebas`, con el simulador de API Colombia encendido |
| 02 | [`02-docker-compose-ps.txt`](02-docker-compose-ps.txt) | Los 15 contenedores: las dos migraciones `Exited (0)` y el resto `Up`; los que tienen healthcheck, `(healthy)` | `evidencias_terminal.py estado` (`docker compose ps -a`) |
| 03 | [`03-gateway-correlation-id.txt`](03-gateway-correlation-id.txt) | `POST /api/itineraries` → **201** con el mismo `X-Correlation-ID` que se envió; un `GET` sin el header recibe uno generado por el gateway | `evidencias_terminal.py gateway` (`curl -i`) |
| 04 | [`04-rate-limit-429.txt`](04-rate-limit-429.txt) | De 40 solicitudes seguidas, 21 responden 200 (10 r/s + ráfaga de 20) y el resto **429** `RATE_LIMIT_EXCEEDED` con `Retry-After: 1` | `evidencias_terminal.py rate-limit` |
| 05 | [`05-notification-history.txt`](05-notification-history.txt) | El evento del itinerario de la evidencia 03, publicado en `outbox_events` y registrado como **SENT** en `notification_history` (otra base) con el mismo `event_id` y `correlation_id`; el log del correo simulado | `evidencias_terminal.py notificacion` (`psql` en los dos contenedores) |
| 06 | [`06-outbox-rabbitmq-detenido.txt`](06-outbox-rabbitmq-detenido.txt) | Transactional Outbox: con RabbitMQ detenido, la API responde 201, el evento queda **pendiente** (`published_at` vacío, `attempts` creciendo) y el relay registra los fallos; al volver RabbitMQ se publica y llega a `notification_history` | `evidencias_terminal.py outbox` (`docker compose stop`/`up rabbitmq`) |
| 07 | [`07-dlq-evento-invalido.txt`](07-dlq-evento-invalido.txt) | Un evento que no cumple el contrato: el trigger registra el rechazo (fallo permanente) y la DLQ queda con 1 mensaje | `evidencias_terminal.py dlq` (API del panel de RabbitMQ) |
| 08 | [`08-swagger-airport.png`](08-swagger-airport.png) | Swagger de Airport Service (`http://localhost:8001/docs`) con sus endpoints | `capturar_evidencias.py swagger` |
| 09 | [`09-swagger-itinerary.png`](09-swagger-itinerary.png) | Swagger de Itinerary Service (`http://localhost:8002/docs`) con el CRUD | `capturar_evidencias.py swagger` |
| 10 | [`10-frontend-mapa.png`](10-frontend-mapa.png) | Mapa de Plotly con **51 aeropuertos** (el 43 no tiene coordenadas) y un color por tipo | `capturar_evidencias.py frontend` |
| 11 | [`11-frontend-crear.png`](11-frontend-crear.png) | CRUD, crear: formulario lleno (María Rodríguez, Armenia → Cali, 80 min) antes de guardar | `capturar_evidencias.py frontend` |
| 12 | [`12-frontend-consultar.png`](12-frontend-consultar.png) | CRUD, consultar: el itinerario nuevo en la tabla, con los aeropuertos por nombre | `capturar_evidencias.py frontend` |
| 13 | [`13-frontend-actualizar.png`](13-frontend-actualizar.png) | CRUD, actualizar: la misma fila con la duración cambiada a 95 min | `capturar_evidencias.py frontend` |
| 14 | [`14-frontend-eliminar.png`](14-frontend-eliminar.png) | CRUD, eliminar: tras confirmar, la fila ya no está | `capturar_evidencias.py frontend` |
| 15 | [`15-jaeger-traza.png`](15-jaeger-traza.png) | La traza del `POST` de la evidencia 03 con **6 servicios**: gateway → Itinerary → Airport (dos validaciones) → PostgreSQL → Outbox Relay → Event Trigger → función | `capturar_evidencias.py jaeger` |
| 16 | [`16-grafana-dashboard.png`](16-grafana-dashboard.png) | Dashboard "Sistema de Itinerarios Personales": itinerarios creados, notificaciones, mensajes en DLQ (1, igual que RabbitMQ), solicitudes, latencias, relay y trigger | `capturar_evidencias.py grafana` |
| 17 | [`17-rabbitmq-colas.png`](17-rabbitmq-colas.png) | Panel de RabbitMQ: la cola `notification.itinerary-created` vacía y con su consumidor, y `notification.itinerary-created.dlq` con 1 mensaje | `capturar_evidencias.py rabbitmq` |
| 18 | [`18-rabbitmq-dlq-mensaje.png`](18-rabbitmq-dlq-mensaje.png) | El mensaje de la DLQ leído sin sacarlo de la cola: header `x-death` con `reason: rejected` y la cola de origen | `capturar_evidencias.py rabbitmq` |
| 19 | [`19-sonarcloud.png`](19-sonarcloud.png) | Resumen de SonarCloud sobre `main` en *Overall Code* (análisis del commit `baaf05a9`, merge del PR #33): Quality Gate **aprobado**, seguridad **A** (0 problemas), fiabilidad **A** (0 problemas), mantenibilidad **A** (32 problemas), 0 problemas aceptados y **2,2 %** de duplicación | Captura manual en sonarcloud.io, tomada por el equipo |
| 20 | [`20-github-actions.png`](20-github-actions.png) | Los **8 checks** del pull request de la Fase 12 (#30) en verde ("All checks have passed"): los 7 jobs del workflow "Pruebas" (Airport Service, API Gateway, Docker Compose, Event Trigger, Itinerary Service, libs/observability y SendNotificationFunction) y *SonarCloud Code Analysis* con "Quality Gate passed" | Captura manual del pull request en GitHub, tomada por el equipo |

Notas para leerlas:

- **Evidencia 15.** Jaeger marca la traza como *Incomplete* porque el span padre lo envió `curl` en el header
  `traceparent` (para fijar un trace ID conocido) y `curl` no reporta spans. El resto de la traza está completa. El
  relay aparece unos dos segundos después del `POST`: es su intervalo de revisión de la outbox.
- **Evidencias 03, 05 y 06.** Los correlation ID llevan la fecha y hora de la sesión (`evidencia-20261118230006`) para
  no mezclarse con los de otra ejecución.
- **Evidencia 06.** `last_error` conserva el último error aunque el evento ya se haya publicado: queda como registro de
  los intentos fallidos.

## Cómo regenerarlas

Herramientas: los dos scripts de `scripts/`. `evidencias_terminal.py` solo usa la librería estándar de Python, `docker`
y `curl`. `capturar_evidencias.py` usa **Playwright** (herramienta de desarrollo, aprobada en la Fase 12), instalado en
su propio entorno virtual `scripts/.venv`, fuera de los `requirements` de los servicios. Las pruebas de la evidencia 01
usan el entorno virtual de cada componente (CLAUDE.md, sección 4.3).

### 1. Instalar Playwright (una vez)

**PowerShell:**

```powershell
py -3.12 -m venv scripts\.venv
.\scripts\.venv\Scripts\Activate.ps1
python -m pip install -r scripts\requirements-evidencias.txt
python -m playwright install chromium
deactivate
```

**CMD:**

```cmd
py -3.12 -m venv scripts\.venv
scripts\.venv\Scripts\activate.bat
python -m pip install -r scripts\requirements-evidencias.txt
python -m playwright install chromium
deactivate
```

**macOS (zsh):**

```bash
python3.12 -m venv scripts/.venv
source scripts/.venv/bin/activate
python -m pip install -r scripts/requirements-evidencias.txt
python -m playwright install chromium
deactivate
```

`playwright install chromium` descarga el navegador (unos 150 MB) en la carpeta del usuario
(`%USERPROFILE%\AppData\Local\ms-playwright` en Windows, `~/Library/Caches/ms-playwright` en macOS).

### 2. Evidencia 01, con el simulador de API Colombia

Desde la raíz del repositorio. Los comandos `docker` son iguales en las tres terminales:

```bash
docker compose -f docker-compose.yml -f docker-compose.e2e.yml up -d --build --wait
```

```bash
docker compose restart api-gateway
```

El reinicio del gateway hace falta porque Airport Service se recreó con otra IP (ADR-041). Después:
`py -3.12 scripts\evidencias_terminal.py pruebas` (PowerShell y CMD) o `python3.12 scripts/evidencias_terminal.py pruebas`
(zsh).

### 3. Volver a la API Colombia real

```bash
docker compose up -d --wait --remove-orphans
```

```bash
docker compose restart api-gateway
```

```bash
docker compose exec redis redis-cli FLUSHALL
```

`FLUSHALL` vacía la caché de Airport Service, que todavía tiene los 5 aeropuertos del simulador; sin ese paso el mapa
mostraría 4. Es solo caché: se vuelve a llenar con la primera consulta.

Para que la DLQ de RabbitMQ y el panel "Mensajes en DLQ" de Grafana muestren el mismo número, la DLQ debe empezar
vacía (revisar antes qué contiene: puede tener mensajes reales) y el contador del trigger en cero:
`docker compose restart event-trigger`.

### 4. Evidencias 02 a 07

**PowerShell y CMD:**

```cmd
py -3.12 scripts\evidencias_terminal.py
```

**macOS (zsh):**

```bash
python3.12 scripts/evidencias_terminal.py
```

Sin argumentos ejecuta, en orden, `estado gateway notificacion outbox rate-limit dlq` (unos 40 s; el paso `outbox`
detiene y vuelve a levantar RabbitMQ). Cada paso se puede ejecutar solo, por ejemplo `... evidencias_terminal.py estado`.

### 5. Evidencias 08 a 18

**PowerShell y CMD:**

```cmd
scripts\.venv\Scripts\python.exe scripts\capturar_evidencias.py
```

**macOS (zsh):**

```bash
scripts/.venv/bin/python scripts/capturar_evidencias.py
```

Se puede limitar a algunas páginas: `... capturar_evidencias.py frontend jaeger`. La traza de Jaeger es la del paso
`gateway` (el script lee su trace ID de la evidencia 03). El usuario y la clave del panel de RabbitMQ (`guest`) y de
Grafana (`admin`) son los de desarrollo local de `docker-compose.yml` y `.env.example`.

### 6. Evidencias 19 y 20 (manuales)

No se generan con los scripts: son capturas de las páginas de SonarCloud y de GitHub. Para actualizarlas, reemplazar
la imagen en esta carpeta con el mismo nombre y ajustar su descripción en la tabla de arriba y en la sección
[Evidencias](../../README.md#evidencias) del README raíz.
