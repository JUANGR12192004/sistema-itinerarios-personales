
# 07. Ejecución manual (modo desarrollo)

> Este contenido estaba en el `README.md` raíz hasta la Fase 11 y se movió aquí en la Fase 12, sin cambios de fondo.
> La forma recomendada de levantar el sistema es **Docker Compose**: ver
> [Instalación y ejecución](../README.md#instalación-y-ejecución) en el README raíz.

**Contenido:** [1. Contenedores de infraestructura](#1-contenedores-de-infraestructura) ·
[2. Observabilidad](#2-observabilidad-fase-9) · [3. Migraciones](#3-migraciones) ·
[4. SendNotificationFunction](#4-sendnotificationfunction) · [5 a 8. Procesos de Python](#5-a-8-procesos-de-python) ·
[9. API Gateway](#9-api-gateway) · [Qué pasa si se omite un paso](#qué-pasa-si-se-omite-un-paso)

Todos los comandos se ejecutan **desde la raíz del repositorio**, salvo los que indican otra carpeta.

Antes de la Fase 10 el sistema se levantaba solo a mano. Sigue siendo útil para **desarrollar un componente** con
recarga automática o depurarlo desde el entorno virtual, pero no a la vez que Docker Compose (mismos puertos). El
orden importa porque cada paso necesita los anteriores. La instalación de cada componente (entorno virtual, `.env`)
está en su README; aquí está el orden para levantarlo todo.

> **Combinar los dos modos:** se puede tener casi todo en Compose y un componente en el equipo, siempre que ningún
> contenedor necesite llamar a ese componente (los contenedores lo buscan por su nombre de servicio, no en el
> equipo). Funciona con el **Outbox Relay** y el **Event Trigger**: `docker compose stop outbox-relay` y después
> `python -m app.outbox_relay` desde el entorno virtual, con su `.env` de siempre (`localhost:5433`,
> `localhost:5672`). No funciona con Airport o Itinerary Service, porque el gateway los llama por su nombre.

## 1. Contenedores de infraestructura

Igual en PowerShell, CMD y la Terminal de macOS (zsh). En Apple Silicon las imágenes se descargan para `arm64`
sin opciones adicionales. **La primera vez** se crean:

```
docker network create notification-net
docker run -d --name itinerary-postgres -e POSTGRES_USER=itinerary -e POSTGRES_PASSWORD=itinerary -e POSTGRES_DB=itinerary_db -p 5433:5432 postgres:16-alpine
docker run -d --name itinerary-rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.13-management
docker run -d --name notification-postgres --network notification-net -p 5434:5432 -e POSTGRES_USER=notification -e POSTGRES_PASSWORD=notification -e POSTGRES_DB=notification_db postgres:16-alpine
docker run -d --name airport-redis -p 6379:6379 redis:7.4-alpine
```

**Las veces siguientes** basta con encenderlos:

```
docker start itinerary-postgres itinerary-rabbitmq notification-postgres airport-redis
```

RabbitMQ tarda unos segundos: está listo cuando `docker logs itinerary-rabbitmq` muestra `Server startup complete`.

## 2. Observabilidad (Fase 9)

Stack de observabilidad (Jaeger, Prometheus y Grafana). Es opcional para los pasos siguientes; sin él el sistema
funciona igual, pero no se ven trazas ni métricas.

Prometheus y Grafana comparten la red Docker `observability-net`: el datasource de Grafana busca a Prometheus por
el nombre `prometheus` (`observability/grafana/provisioning/datasources/prometheus.yml`), y ese nombre solo se
resuelve dentro de una red Docker común. Grafana monta además la carpeta `dashboards/`, de donde carga el dashboard.
Prometheus llega a los servicios del equipo por `host.docker.internal` (`observability/prometheus/prometheus.yml`).

**La primera vez** se crean. **CMD:**

```cmd
docker network create observability-net
docker run -d --name jaeger -p 16686:16686 -p 4317:4317 jaegertracing/jaeger:2.23.0 --set receivers.otlp.protocols.grpc.endpoint=0.0.0.0:4317
docker run -d --name prometheus --network observability-net -p 9090:9090 -v "%CD%\observability\prometheus\prometheus.yml:/etc/prometheus/prometheus.yml" prom/prometheus:v2.55.0
docker run -d --name grafana --network observability-net -p 3000:3000 -v "%CD%\observability\grafana\provisioning:/etc/grafana/provisioning" -v "%CD%\observability\grafana\dashboards:/var/lib/grafana/dashboards" grafana/grafana:11.3.1
```

**PowerShell** (la carpeta actual es `${PWD}`, no `%CD%`):

```powershell
docker network create observability-net
docker run -d --name jaeger -p 16686:16686 -p 4317:4317 jaegertracing/jaeger:2.23.0 --set receivers.otlp.protocols.grpc.endpoint=0.0.0.0:4317
docker run -d --name prometheus --network observability-net -p 9090:9090 -v "${PWD}\observability\prometheus\prometheus.yml:/etc/prometheus/prometheus.yml" prom/prometheus:v2.55.0
docker run -d --name grafana --network observability-net -p 3000:3000 -v "${PWD}\observability\grafana\provisioning:/etc/grafana/provisioning" -v "${PWD}\observability\grafana\dashboards:/var/lib/grafana/dashboards" grafana/grafana:11.3.1
```

**macOS (zsh):**

```bash
docker network create observability-net
docker run -d --name jaeger -p 16686:16686 -p 4317:4317 jaegertracing/jaeger:2.23.0 --set receivers.otlp.protocols.grpc.endpoint=0.0.0.0:4317
docker run -d --name prometheus --network observability-net -p 9090:9090 -v "$(pwd)/observability/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml" prom/prometheus:v2.55.0
docker run -d --name grafana --network observability-net -p 3000:3000 -v "$(pwd)/observability/grafana/provisioning:/etc/grafana/provisioning" -v "$(pwd)/observability/grafana/dashboards:/var/lib/grafana/dashboards" grafana/grafana:11.3.1
```

**Las veces siguientes:** `docker start jaeger prometheus grafana`.

> *Corrección (Fase 12):* hasta la Fase 11 estos comandos no usaban la red `observability-net` ni montaban
> `dashboards/`. Con ellos Grafana arrancaba sin dashboard y su datasource fallaba
> (`lookup prometheus: no such host`). Se comprobó el 2026-11-18 en macOS: con los comandos de arriba el dashboard
> "Sistema de Itinerarios Personales" se carga, el datasource responde y los cuatro destinos de Prometheus están `up`.
> Si los contenedores ya existían, se borran con `docker rm -f prometheus grafana` y se crean de nuevo.

Interfaces:

- Jaeger: <http://localhost:16686>
- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3000> (usuario `admin`, clave `admin`)

> Las trazas llegan a Jaeger porque los servicios, el relay y el trigger se inician con `OTEL_ENABLED=true` (valor
> por defecto). Para desactivarlas: `OTEL_ENABLED=false` como variable de entorno antes de arrancar cada proceso.

## 3. Migraciones

Una vez, y otra cada vez que lleguen migraciones nuevas. Con el entorno virtual de cada carpeta activado.

**PowerShell:**

```powershell
cd services\itinerary-service
.\.venv\Scripts\Activate.ps1
alembic upgrade head
deactivate
cd ..\..\serverless\send-notification-function
.\.venv\Scripts\Activate.ps1
alembic upgrade head
deactivate
cd ..\..
```

**CMD:**

```cmd
cd services\itinerary-service
.venv\Scripts\activate.bat
alembic upgrade head
deactivate
cd ..\..\serverless\send-notification-function
.venv\Scripts\activate.bat
alembic upgrade head
deactivate
cd ..\..
```

**macOS (zsh):**

```bash
cd services/itinerary-service
source .venv/bin/activate
alembic upgrade head
deactivate
cd ../../serverless/send-notification-function
source .venv/bin/activate
alembic upgrade head
deactivate
cd ../..
```

## 4. SendNotificationFunction

Igual en PowerShell, CMD y zsh, **desde la raíz del repositorio** (el contexto de build incluye `libs/`).
La primera vez (y después de cada cambio en el código de la función) se construye la imagen y se crea el
contenedor:

```
docker build -t send-notification-function -f serverless/send-notification-function/Dockerfile .
docker run -d --name send-notification-function --network notification-net -p 9000:8080 -e DATABASE_URL=postgresql+psycopg://notification:notification@notification-postgres:5432/notification_db send-notification-function
```

Las veces siguientes: `docker start send-notification-function`.

En Apple Silicon la imagen se construye para `arm64` (la imagen base de Lambda trae las dos arquitecturas). Funciona
igual en local; solo importa al desplegar en AWS Lambda, donde la función se crearía con arquitectura `arm64` (o la
imagen se construiría con `docker build --platform linux/amd64`).

## 5 a 8. Procesos de Python

Cada uno en **su propia terminal**, con el entorno virtual de su carpeta activado
(`.\.venv\Scripts\Activate.ps1` en PowerShell, `.venv\Scripts\activate.bat` en CMD, `source .venv/bin/activate` en
zsh). Los comandos son iguales en las tres terminales (en macOS, las carpetas se escriben con `/`):

| Paso | Carpeta | Comando | Listo cuando |
|---|---|---|---|
| 5. Airport Service | `services\airport-service` | `uvicorn app.main:app --port 8001` | http://localhost:8001/health responde |
| 6. Itinerary Service | `services\itinerary-service` | `uvicorn app.main:app --port 8002` | http://localhost:8002/health responde |
| 7. Outbox Relay | `services\itinerary-service` | `python -m app.outbox_relay` | `Outbox Relay iniciado` |
| 8. Event Trigger | `serverless\event-trigger` | `python -m app.main` | `escuchando la cola notification.itinerary-created` |

## 9. API Gateway

Igual en PowerShell, CMD y zsh, desde la raíz del repositorio. La primera vez (y después de cada cambio en
`gateway/templates/`) se construye la imagen y se crea el contenedor:

```
docker build -t api-gateway -f gateway/Dockerfile .
docker run -d --name api-gateway -p 8000:8000 api-gateway
```

Las veces siguientes: `docker start api-gateway`. Está listo cuando http://localhost:8000/health responde.

El gateway puede arrancar antes que los servicios: mientras un servicio no esté corriendo, sus rutas responden 502
`UPSTREAM_UNAVAILABLE`, y en cuanto arranca, funcionan sin reiniciar el gateway. Llega a los servicios del equipo por
`host.docker.internal` (Docker Desktop lo crea en macOS y Windows).

Para detener todo: Ctrl+C en cada terminal y `docker stop api-gateway send-notification-function notification-postgres itinerary-rabbitmq itinerary-postgres airport-redis grafana prometheus jaeger`.

## Qué pasa si se omite un paso

| Paso omitido | Qué se ve | Cómo se corrige |
|---|---|---|
| `itinerary-postgres` | `POST /itineraries` responde 500 y el relay registra un error en cada ciclo | Encenderlo; el relay sigue solo |
| `itinerary-rabbitmq` | El relay no puede publicar: los eventos **esperan en la outbox**. El trigger reintenta la conexión cada 5 s | Encenderlo; todo se publica y se procesa solo |
| `notification-postgres` | La función responde `TransientError`; el trigger reintenta **sin límite** y nada va a la DLQ | Encenderlo; los mensajes se procesan solos |
| `airport-redis` | Airport Service funciona sin caché (registra un warning) | Opcional |
| Migración de `itinerary_db` | `POST /itineraries` responde 500 (la tabla no existe) | `alembic upgrade head` en Itinerary Service |
| Migración de `notification_db` | La función falla con `ProgrammingError`, que **no** es `TransientError`: tras 3 intentos los mensajes terminan en la **DLQ** | `alembic upgrade head` en la función y después `python -m app.replay_dlq --all` en el trigger |
| SendNotificationFunction | El trigger no puede conectarse: reintenta sin límite, nada va a la DLQ | Encenderla; los mensajes se procesan solos |
| Airport Service | `POST /itineraries` responde 503 `AIRPORT_SERVICE_UNAVAILABLE` y no se guarda nada | Arrancarlo y repetir la solicitud |
| Itinerary Service | No se pueden crear itinerarios | Arrancarlo |
| Outbox Relay | Los itinerarios se crean (201), pero sus eventos **se acumulan pendientes en la outbox** | Arrancarlo; publica los pendientes en orden |
| Event Trigger (nunca arrancó) | La cola no existe: el relay registra `UnroutableError` y el evento **espera en la outbox** | Arrancarlo: declara la cola y el relay publica en el siguiente ciclo |
| Event Trigger (apagado después) | Los mensajes se acumulan en la cola (*Ready* en el panel) | Arrancarlo; los procesa en orden |
| API Gateway | `http://localhost:8000` rechaza la conexión. Los servicios siguen respondiendo directamente en 8001 y 8002 | `docker start api-gateway` (o los comandos del paso 9 la primera vez) |
| Airport o Itinerary Service, usando el gateway | El gateway responde 502 `UPSTREAM_UNAVAILABLE` con `details.service` | Arrancar el servicio; no hace falta reiniciar el gateway |
| Jaeger | Los servicios funcionan con normalidad; el exportador OTLP registra un error al arrancar pero no interrumpe nada | `docker start jaeger` |
| Prometheus | Los servicios funcionan; el endpoint `/metrics` sigue disponible pero nadie lo consulta | `docker start prometheus` |
| Grafana | Los servicios y Prometheus funcionan; no hay dashboard | `docker start grafana` |
