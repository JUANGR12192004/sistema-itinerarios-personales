
# Sistema de Itinerarios Personales

Sistema distribuido para la planificación y gestión de itinerarios de viaje, desarrollado como proyecto académico para la asignatura **Arquitecturas de Software Emergentes**.

El proyecto busca aplicar tres enfoques arquitectónicos: microservicios, arquitectura basada en eventos y arquitectura serverless.

## Objetivo general

Diseñar e implementar un sistema distribuido que permita consultar aeropuertos colombianos, gestionar itinerarios de viaje y procesar notificaciones de forma asíncrona, aplicando principios de modularidad, desacoplamiento, resiliencia y observabilidad.

## Objetivos específicos

- Consultar aeropuertos colombianos mediante la API pública API Colombia.
- Desacoplar la integración externa mediante el patrón Adapter.
- Visualizar aeropuertos en un mapa interactivo con Plotly JS.
- Implementar operaciones CRUD para itinerarios.
- Validar aeropuertos mediante comunicación HTTP entre microservicios.
- Publicar eventos de integración mediante RabbitMQ.
- Procesar notificaciones con una función serverless.
- Aplicar arquitectura hexagonal y conceptos básicos de Domain-Driven Design (DDD).
- Incorporar persistencia independiente, migraciones, pruebas y documentación de API.
- Preparar mecanismos de resiliencia, caché y observabilidad.

## Alcance

El sistema estará compuesto por:

1. **Airport Service:** consulta y normalización de información de aeropuertos.
2. **Itinerary Service:** creación, consulta, actualización y eliminación de itinerarios, con su Outbox Relay.
3. **Sistema de notificaciones:** Event Trigger + SendNotificationFunction + su base de datos.
4. **SendNotificationFunction:** función serverless que simula la notificación y guarda el historial.
5. **API Gateway (Nginx):** punto único de entrada en el puerto 8000; enruta, limita solicitudes y propaga headers, sin lógica de negocio.
6. **Frontend:** interfaz de gestión de itinerarios y visualización de aeropuertos.

La implementación se desarrolla progresivamente, siguiendo las fases definidas en la documentación del proyecto.

## Tecnologías

| Área | Tecnología |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic |
| Persistencia | PostgreSQL (una base por servicio) |
| ORM y migraciones | SQLAlchemy y Alembic |
| Comunicación síncrona | HTTP / REST |
| API Gateway | Nginx (imagen oficial `nginx:1.30.6-alpine`, ADR-009) |
| Mensajería | RabbitMQ (pika) |
| Caché | Redis |
| Serverless | Imagen oficial de AWS Lambda para Python 3.12 con el Runtime Interface Emulator (ADR-008) |
| Frontend | HTML, CSS, JavaScript |
| Visualización | Plotly JS |
| Contenedores | Docker y Docker Compose (`docker-compose.yml` en la raíz, ADR-041) |
| Observabilidad | OpenTelemetry, Jaeger, Prometheus y Grafana |
| Documentación API | Swagger / OpenAPI y AsyncAPI |
| Pruebas | pytest, TestClient de FastAPI y respx |

## Arquitectura

El sistema utiliza microservicios con responsabilidades delimitadas, comunicación HTTP para las operaciones que necesitan una respuesta inmediata y mensajería asíncrona para los eventos de integración.

Cada microservicio de negocio tiene su propia base de datos y es responsable de sus propios datos.

Se aplican arquitectura hexagonal, el patrón Adapter y conceptos de DDD para mantener separadas las reglas de negocio y los detalles de infraestructura.

```mermaid
flowchart LR
    C[Cliente] -->|POST /api/itineraries| GW["API Gateway (Nginx) :8000"]
    GW -->|/api/airports| AS[Airport Service :8001]
    GW -->|POST /itineraries| IS[Itinerary Service :8002]
    IS -->|"HTTP: validar aeropuertos"| AS
    AS --> EXT[API Colombia]
    IS -->|"itinerario + evento,<br/>misma transacción"| DBI[(itinerary_db :5433)]
    DBI --> R[Outbox Relay]
    R -->|itinerary.events| MQ[RabbitMQ :5672]
    MQ -->|notification.itinerary-created| T[Event Trigger]
    T -->|"HTTP: API Invoke de Lambda"| F["SendNotificationFunction<br/>(Lambda + RIE :9000)"]
    F --> DBN[(notification_db :5434)]
    MQ -.rechazados.-> DLQ[(DLQ)]
```

Todos los diagramas están en [`docs/05-diagramas.md`](docs/05-diagramas.md).

## Estructura documental

- `docs/01-planificacion.md`: objetivos, alcance, requisitos y fases.
- `docs/02-arquitectura.md`: arquitectura general y responsabilidades.
- `docs/03-dominio.md`: dominio, contextos delimitados y lenguaje ubicuo.
- `docs/04-comunicacion-y-eventos.md`: comunicación HTTP, eventos, Outbox y serverless (FaaS, Event Trigger, DLQ).
- `docs/05-diagramas.md`: diagramas arquitectónicos en Mermaid.
- `docs/06-decisiones-arquitectonicas.md`: registro de decisiones técnicas (ADR).
- `docs/asyncapi/asyncapi.yaml`: contrato del evento `ItineraryCreatedEvent` y cómo se publica y se consume.

| Componente | Documentación |
|---|---|
| API Gateway | [`gateway/README.md`](gateway/README.md) |
| Airport Service | [`services/airport-service/README.md`](services/airport-service/README.md) |
| Itinerary Service y Outbox Relay | [`services/itinerary-service/README.md`](services/itinerary-service/README.md) |
| SendNotificationFunction | [`serverless/send-notification-function/README.md`](serverless/send-notification-function/README.md) |
| Event Trigger y reprocesamiento de la DLQ | [`serverless/event-trigger/README.md`](serverless/event-trigger/README.md) |

## Estado del proyecto

| Fase | Nombre | Estado |
|---|---|---|
| 0 | Planificación y arquitectura | Completada |
| 1 | Airport Service | Completada |
| 2 | Resiliencia y caché | Completada |
| 3 | Itinerary Service | Completada |
| 4 | Eventos y RabbitMQ | Completada |
| 5 | Transactional Outbox | Completada |
| 6 | Serverless | Completada |
| 7 | API Gateway | Completada |
| 8 | Frontend | Completada |
| 9 | Observabilidad | Completada |
| 10 | Docker y Docker Compose | Completada (rama `fase-10-docker-compose`) |
| 11 | Pruebas | Completada (rama `fase-11-pruebas`) |
| 12 | Documentación y entrega | Pendiente |

**Última fase completada:** Fase 11 — Pruebas. **Siguiente:** Fase 12 — Documentación y entrega.

El equipo trabaja en **Windows 11** (PowerShell y CMD) y en **macOS con Apple Silicon** (zsh). Los README dan los
comandos para las tres terminales; la tabla de equivalencias está en [`CLAUDE.md`](CLAUDE.md), sección 4.2.

### Fase 11 — Pruebas

Pirámide de pruebas en cinco niveles (ADR-042; cómo correr cada uno en [Pruebas](#pruebas)):

- **Bases propias de las pruebas de integración**: `itinerary_db_test` y `notification_db_test`, creadas y migradas
  por las propias pruebas. Ya no borran datos de las bases reales.
- **Pruebas de `libs/observability`** con su job de CI.
- **Pruebas de contrato**: Airport Service publica su API en `docs/openapi/airport-service.json` e Itinerary Service
  la verifica como consumidor; SendNotificationFunction verifica el evento contra AsyncAPI.
- **Pruebas de punta a punta** (`tests/e2e`) sobre Docker Compose con un simulador de API Colombia
  (`docker-compose.e2e.yml`): CRUD, outbox → RabbitMQ → función → historial, una traza en Jaeger con los seis
  componentes y métricas en Prometheus. Las ejecuta el job "Docker Compose" del CI.
- **Salida limpia**: las advertencias de Starlette y pika (de terceros) se filtran con precisión.

Con todo encendido: **639 pruebas, 0 fallos, 0 omitidas**.

### Fase 10 — Docker y Docker Compose

Todo el sistema se levanta con **un solo comando**: `docker compose up -d --build` (ADR-041). Solo hace falta Docker
Desktop; Python 3.12 sigue haciendo falta para desarrollar y ejecutar las pruebas. Ver
[Arranque con Docker Compose](#arranque-con-docker-compose-recomendado).

| Pieza | Qué hace |
|---|---|
| Imágenes propias | Airport Service, Itinerary Service (una imagen para la API, el relay y las migraciones), Event Trigger y migraciones de notificaciones, sobre `python:3.12-slim` con usuario sin privilegios |
| Migraciones automáticas | `itinerary-migrations` y `notification-migrations` aplican `alembic upgrade head` y terminan; la API, el relay y la función esperan a que terminen con éxito |
| Orden de arranque con healthchecks | `depends_on` espera a que PostgreSQL y RabbitMQ estén listos: ya no hay que seguir el orden a mano |
| Redes por base de datos | Cada PostgreSQL solo es visible para los contenedores de su servicio dueño |
| Mismos puertos de siempre | Gateway 8000, servicios 8001/8002, bases 5433/5434, RabbitMQ 5672/15672, Jaeger 16686, Prometheus 9090, Grafana 3000 |
| Observabilidad incluida | Jaeger, Prometheus (`prometheus.compose.yml`) y Grafana con el dashboard cargado al arrancar |
| CI | Job "Docker Compose": valida el archivo, construye las imágenes, levanta el sistema y comprueba los healthchecks y el gateway |

### Fase 9 — Observabilidad

Logs JSON estructurados, trazas distribuidas con OpenTelemetry y métricas con Prometheus y Grafana en todos los componentes (ADR-034 a ADR-040). El código de observabilidad compartido se consolidó en el paquete `libs/observability` (Microservice Chassis Pattern, ADR-040), incluido automáticamente al instalar las dependencias de cada componente.

| Pieza | Qué hace |
|---|---|
| Logs JSON (`python-json-logger`) | Cada línea incluye `timestamp`, `level`, `service`, `correlation_id`, `trace_id` y `span_id`. Mismo patrón en los cuatro componentes Python |
| Trazas (OpenTelemetry SDK + Jaeger 2.23.0) | Propaga el contexto W3C por toda la cadena: gateway → servicios → outbox → relay → RabbitMQ → trigger → función. El `traceparent` se guarda en `outbox_events` para cruzar la barrera de procesos (ADR-037) |
| API Gateway con `ngx_otel_module` | Imagen `nginx:1.30.6-alpine-otel`: inyecta `traceparent` en las solicitudes hacia los servicios y registra `trace_id` y `span_id` en su log de acceso (ADR-036) |
| Métricas HTTP (middleware en Airport e Itinerary Service) | `http_requests_total{method, path, status}` y `http_request_duration_seconds{method, path}`. Ruta como plantilla para evitar explosión de cardinalidad |
| Métrica de negocio | `itineraries_created_total` en Itinerary Service: responde "¿funciona el sistema?" sin abrir logs |
| Métricas del Outbox Relay (puerto 9101) | `outbox_events_published_total`, `outbox_events_failed_total`, `outbox_events_dead_total`, `outbox_relay_cycles_total` |
| Métricas del Event Trigger (puerto 9102) | `notifications_dispatched_total{outcome}`: `success`, `rejected`, `infrastructure_error`, `function_error` |
| Prometheus (puerto 9090) | Consulta los cuatro endpoints cada 15 s. Configurado en `observability/prometheus/prometheus.yml` |
| Grafana (puerto 3000) | Dashboard preconfigurado con paneles de negocio, HTTP, latencia (p50/p95/p99) y relay/trigger. Provisioning automático desde `observability/grafana/provisioning/` |

La demostración completa está en la sección [Demostración de observabilidad](#demostración-de-observabilidad).

### Fase 8 — Frontend

Interfaz web servida por el mismo contenedor del API Gateway. Mapa de aeropuertos con Plotly JS y CRUD de itinerarios (ADR-033).

| Pieza | Qué hace |
|---|---|
| Mapa de aeropuertos | `scattergeo` de Plotly 4.3.0 (bundle parcial local), centrado en Colombia, un color por tipo, tooltip con nombre, IATA, ciudad y departamento |
| CRUD de itinerarios | Formulario de 2 columnas con desplegables de aeropuertos; tabla con edición inline y eliminación con confirmación |
| `datetime-local` → ISO 8601 | La fecha se envía con el offset del navegador (ADR-017) |
| Errores del gateway | Se muestran con `correlation_id` y botón "Copiar" en 5xx |
| Sin `innerHTML` | Todo texto de datos con `textContent` para evitar XSS |

### Fase 7 — API Gateway

Punto único de entrada en `http://localhost:8000`: **Nginx** en Docker, sin lógica de negocio (ADR-009). Toda la
documentación está en [`gateway/README.md`](gateway/README.md).

| Pieza | Qué hace |
|---|---|
| Enrutamiento | `/api/airports/...` → Airport Service y `/api/itineraries/...` → Itinerary Service, sin el prefijo `/api`. La llamada Itinerary → Airport es interna y no pasa por el gateway |
| Rate limiting | 10 solicitudes por segundo por IP, con ráfaga de 20, solo en `/api/`. Al superarlo: 429 `RATE_LIMIT_EXCEEDED` |
| `X-Correlation-ID` | Se reenvía si es válido; si no, el gateway genera uno. Viaja al evento y al historial de notificaciones |
| `Authorization` | Se reenvía sin validarlo (preparación de JWT) |
| Errores propios | 502 `UPSTREAM_UNAVAILABLE`, 504 `UPSTREAM_TIMEOUT`, 404 `ROUTE_NOT_FOUND`, 413 `PAYLOAD_TOO_LARGE` en el formato único. Los errores de los servicios pasan sin cambios |
| Pruebas | Contenedores propios del gateway contra servidores eco: no tocan datos reales ni el límite del gateway de la demostración |

### Fase 6 — Serverless

| Pieza | Qué hace |
|---|---|
| SendNotificationFunction | Función FaaS `handler(event, context)` en una imagen de AWS Lambda con el RIE (puerto 9000). Simula el correo y guarda el historial en `notification_db`, de forma idempotente con `event_id` (ADR-008, ADR-028 a ADR-030) |
| Event Trigger (`python -m app.main`) | Equivalente al Event Source Mapping de AWS: consume la cola, invoca la función y confirma, reintenta o envía a la DLQ (ADR-031) |
| Fallo de infraestructura | Función o su base de datos caídas: se reintenta sin límite y nunca va a la DLQ |
| Fallo permanente o error de la función | Evento inválido: a la DLQ sin reintentos. Error de la función: 3 intentos y después a la DLQ |
| Reprocesamiento (`python -m app.replay_dlq`) | Devuelve a la cola los mensajes de la DLQ una vez corregido el problema |
| Propiedad de la topología | Itinerary Service declara solo su exchange; el trigger declara su cola, la DLX y la DLQ. Si el trigger no ha arrancado, el evento espera en la outbox (ADR-032) |

La explicación completa (qué es FaaS y por qué esta función lo es aunque corra en Docker) está en
[`docs/04-comunicacion-y-eventos.md`](docs/04-comunicacion-y-eventos.md), sección 8.

### Fase 5 — Transactional Outbox

Resuelve el problema de *double write* de la Fase 4 (guardar en PostgreSQL y publicar en RabbitMQ sin una transacción común), sin cambiar el contrato del evento.

| Pieza | Qué hace |
|---|---|
| Tabla `outbox_events` | Guarda el evento en la **misma transacción** que el itinerario: se guardan los dos o ninguno (ADR-024, ADR-026) |
| Outbox Relay (`python -m app.outbox_relay`) | Proceso aparte que publica los pendientes con `FOR UPDATE SKIP LOCKED` y los marca como publicados (ADR-025) |
| Fallo temporal (RabbitMQ caído) | El evento sigue pendiente y se reintenta sin límite: no se pierde |
| Fallo permanente (mensaje ilegible) | Se descarta con `failed_at` para que no bloquee a los demás (ADR-027) |
| Entrega al menos una vez | Puede haber duplicados: el consumidor debe ser idempotente con `event_id` |

La explicación completa está en [`docs/04-comunicacion-y-eventos.md`](docs/04-comunicacion-y-eventos.md) (sección 7).

### Fase 2 — Resiliencia y caché

Airport Service tolera los fallos de API Colombia sin cambiar sus casos de uso ni el Adapter: la caché y la resiliencia se agregan como Decorators del puerto `AirportProvider`.

| Mecanismo | Comportamiento |
|---|---|
| Caché en Redis | Respuestas guardadas 10 minutos; header `X-Cache: HIT` o `MISS` |
| Timeout | 3 s por llamada; si se agota en todos los intentos → 504 `AIRPORT_PROVIDER_TIMEOUT` |
| Retry con exponential backoff | 3 intentos con esperas de 0.5 s y 1 s; no se reintentan 404 ni 502 |
| Circuit breaker | Tras 3 consultas fallidas seguidas responde 503 al instante durante 30 s |
| Fallback | Si API Colombia no está disponible, responde la copia de respaldo (24 h) con `X-Cache: STALE` |

Orden: caché → circuit breaker → retry con backoff → llamada con timeout → fallback. Si Redis no está disponible, el servicio sigue funcionando sin caché. Decisiones en ADR-007 y ADR-014 (`docs/06-decisiones-arquitectonicas.md`).

## Arranque con Docker Compose (recomendado)

Desde la Fase 10 todo el sistema (15 contenedores) se levanta con Docker Compose. Requisito: **Docker Desktop**
encendido (en Windows con WSL 2; en Mac con Apple Silicon las imágenes se construyen para `arm64` sin opciones
adicionales). Los comandos son **iguales en PowerShell, CMD y la Terminal de macOS (zsh)** y se ejecutan desde la
raíz del repositorio (o cualquier subcarpeta: Compose busca `docker-compose.yml` hacia arriba).

**Si antes se usó el modo manual**, detener esos contenedores, porque ocupan los mismos puertos:

```
docker stop api-gateway send-notification-function notification-postgres itinerary-rabbitmq itinerary-postgres airport-redis grafana prometheus jaeger
```

**Levantar todo** (la primera vez construye las imágenes, unos minutos; las siguientes, segundos):

```
docker compose up -d --build
docker compose ps
```

Listo cuando las dos migraciones aparecen `Exited (0)` y `airport-service`, `itinerary-service` y `api-gateway`
aparecen `healthy`. Entonces:

| Qué | Dónde |
|---|---|
| Frontend (mapa y CRUD) | http://localhost:8000 |
| Swagger de Airport e Itinerary Service | http://localhost:8001/docs y http://localhost:8002/docs |
| Panel de RabbitMQ (`guest` / `guest`) | http://localhost:15672 |
| Jaeger | http://localhost:16686 |
| Prometheus (destinos) | http://localhost:9090/targets |
| Grafana (`admin` / `admin`) | http://localhost:3000 |

**Comandos del día a día:**

| Acción | Comando |
|---|---|
| Ver el estado | `docker compose ps -a` |
| Ver los logs de un componente (Ctrl+C para salir) | `docker compose logs -f outbox-relay` |
| Detener y encender un componente | `docker compose stop event-trigger` / `docker compose start event-trigger` |
| Reconstruir tras un cambio de código | `docker compose up -d --build airport-service` |
| Consultar una base | `docker compose exec itinerary-postgres psql -U itinerary -d itinerary_db` |
| Reprocesar la DLQ | `docker compose run --rm event-trigger python -m app.replay_dlq --all` |
| Detener todo (conserva los datos) | `docker compose down` |
| Detener todo y **borrar** los datos | `docker compose down -v` |

Variables opcionales (nivel de log, trazas, rate limit del gateway, usuario de Grafana): copiar `.env.example` como
`.env` en la raíz (`Copy-Item` en PowerShell, `copy` en CMD, `cp` en zsh). Sin `.env` se usan los mismos valores
por defecto.

### Qué hace Compose por nosotros

La tabla [Qué pasa si se omite un paso](#qué-pasa-si-se-omite-un-paso) describe los errores del modo manual. Con
Compose, `depends_on` impone el orden: las migraciones esperan a su PostgreSQL, la API, el relay y la función esperan
a que su migración termine con éxito, y el relay y el trigger esperan a RabbitMQ. Si un componente se detiene después,
el comportamiento es el de esa tabla (por ejemplo, con `docker compose stop event-trigger` los mensajes se acumulan en
la cola). Detalles en ADR-041 y en el diagrama de despliegue de [`docs/05-diagramas.md`](docs/05-diagramas.md).

### Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| `Bind for 0.0.0.0:5433 failed: port is already allocated` | Hay contenedores del modo manual (o un `uvicorn`) en ese puerto | Detenerlos (comando de arriba) o cerrar el `uvicorn` |
| `dependency failed to start: ... itinerary-migrations exited (1)` | La migración falló | `docker compose logs itinerary-migrations` |
| 502 `UPSTREAM_UNAVAILABLE` justo después de `up` | El servicio aún está arrancando | Esperar a que `docker compose ps` lo muestre `healthy` |
| 502 tras reconstruir un servicio (`up --build <servicio>`) | El contenedor nuevo puede tener otra IP y Nginx guardó la anterior (ADR-041) | `docker compose restart api-gateway` |
| Los datos del modo manual no aparecen | Compose usa sus propios volúmenes | Es lo esperado; las bases empiezan vacías |

## Arranque manual (modo desarrollo)

Antes de la Fase 10 el sistema se levantaba solo a mano. Sigue siendo útil para **desarrollar un componente** con
recarga automática o depurarlo desde el entorno virtual, pero no a la vez que Docker Compose (mismos puertos). El
orden importa porque cada paso necesita los anteriores. La instalación de cada componente (entorno virtual, `.env`)
está en su README; aquí está el orden para levantarlo todo.

> **Combinar los dos modos:** se puede tener casi todo en Compose y un componente en el equipo, siempre que ningún
> contenedor necesite llamar a ese componente (los contenedores lo buscan por su nombre de servicio, no en el
> equipo). Funciona con el **Outbox Relay** y el **Event Trigger**: `docker compose stop outbox-relay` y después
> `python -m app.outbox_relay` desde el entorno virtual, con su `.env` de siempre (`localhost:5433`,
> `localhost:5672`). No funciona con Airport o Itinerary Service, porque el gateway los llama por su nombre.

### 1. Contenedores de infraestructura

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

### 2. Observabilidad (Fase 9)

Stack de observabilidad (Jaeger, Prometheus y Grafana). Es opcional para los pasos siguientes; sin él el sistema
funciona igual, pero no se ven trazas ni métricas. **La primera vez** se crean:

```
docker run -d --name jaeger -p 16686:16686 -p 4317:4317 jaegertracing/jaeger:2.23.0 --set receivers.otlp.protocols.grpc.endpoint=0.0.0.0:4317
docker run -d --name prometheus -p 9090:9090 -v "%CD%\observability\prometheus\prometheus.yml:/etc/prometheus/prometheus.yml" prom/prometheus:v2.55.0
docker run -d --name grafana -p 3000:3000 -v "%CD%\observability\grafana\provisioning:/etc/grafana/provisioning" grafana/grafana:11.3.1
```

En macOS (zsh) reemplazar `%CD%` por `$(pwd)`:

```bash
docker run -d --name jaeger -p 16686:16686 -p 4317:4317 jaegertracing/jaeger:2.23.0 --set receivers.otlp.protocols.grpc.endpoint=0.0.0.0:4317
docker run -d --name prometheus -p 9090:9090 -v "$(pwd)/observability/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml" prom/prometheus:v2.55.0
docker run -d --name grafana -p 3000:3000 -v "$(pwd)/observability/grafana/provisioning:/etc/grafana/provisioning" grafana/grafana:11.3.1
```

**Las veces siguientes:** `docker start jaeger prometheus grafana`.

Interfaces:

- Jaeger: <http://localhost:16686>
- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3000> (usuario `admin`, clave `admin`)

> Las trazas llegan a Jaeger porque los servicios, el relay y el trigger se inician con `OTEL_ENABLED=true` (valor
> por defecto). Para desactivarlas: `OTEL_ENABLED=false` como variable de entorno antes de arrancar cada proceso.

### 3. Migraciones

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

### 4. SendNotificationFunction

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

### 5 a 8. Procesos de Python

Cada uno en **su propia terminal**, con el entorno virtual de su carpeta activado
(`.\.venv\Scripts\Activate.ps1` en PowerShell, `.venv\Scripts\activate.bat` en CMD, `source .venv/bin/activate` en
zsh). Los comandos son iguales en las tres terminales (en macOS, las carpetas se escriben con `/`):

| Paso | Carpeta | Comando | Listo cuando |
|---|---|---|---|
| 5. Airport Service | `services\airport-service` | `uvicorn app.main:app --port 8001` | http://localhost:8001/health responde |
| 6. Itinerary Service | `services\itinerary-service` | `uvicorn app.main:app --port 8002` | http://localhost:8002/health responde |
| 7. Outbox Relay | `services\itinerary-service` | `python -m app.outbox_relay` | `Outbox Relay iniciado` |
| 8. Event Trigger | `serverless\event-trigger` | `python -m app.main` | `escuchando la cola notification.itinerary-created` |

### 9. API Gateway

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

### Qué pasa si se omite un paso

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

## Demostración de observabilidad

Requisitos: el sistema levantado con Docker Compose (incluye Jaeger, Prometheus y Grafana), o los nueve pasos del
arranque manual incluyendo el paso 2. Con Compose, el archivo del itinerario está en
`serverless\event-trigger\demo\create-itinerary.json`: ejecutar el `curl` desde `serverless\event-trigger`.

### Seguir una solicitud de punta a punta en Jaeger

```
curl.exe -s -X POST http://localhost:8000/api/itineraries -H "Content-Type: application/json" -H "X-Correlation-ID: demo-traza" --data-binary "@demo\create-itinerary.json"
```

**macOS (zsh):**

```bash
curl -s -X POST http://localhost:8000/api/itineraries -H "Content-Type: application/json" -H "X-Correlation-ID: demo-traza" --data-binary "@demo/create-itinerary.json"
```

Resultado esperado:

1. La solicitud devuelve 201.
2. En Jaeger (<http://localhost:16686>), buscar el servicio `api-gateway` → aparece la traza que conecta el gateway, Itinerary Service, Airport Service (dos llamadas de validación), la escritura en PostgreSQL y el contexto guardado en la outbox.
3. Unos segundos después, el relay publica el evento: en Jaeger aparece una traza del `itinerary-service-outbox-relay` que continúa el span original gracias al `traceparent` guardado en `outbox_events`.

### Ver métricas en Grafana

Abrir <http://localhost:3000> (usuario `admin`, clave `admin`), ir a **Dashboards → Sistema de Itinerarios Personales**.

- Crear varios itinerarios y observar que `itineraries_created_total` sube.
- El panel "Outbox Relay" muestra los eventos publicados en tiempo real.
- El panel "HTTP Latencia" muestra los percentiles p50, p95 y p99 de los últimos 5 minutos.

Los mismos datos en bruto están en Prometheus (<http://localhost:9090>): buscar `http_requests_total` o `itineraries_created_total`.

## Demostración de punta a punta

Recorrido completo: **gateway** → crear un itinerario → outbox → relay → RabbitMQ → trigger → función → historial.
Requisitos: el sistema levantado con Docker Compose o con los nueve pasos del arranque manual.

> **Con Docker Compose** los contenedores tienen otros nombres (`sistema-itinerarios-<servicio>-1`), así que en los
> comandos de abajo se cambia:
>
> | Modo manual | Docker Compose |
> |---|---|
> | `docker exec notification-postgres ...` | `docker compose exec notification-postgres ...` |
> | `docker exec itinerary-postgres ...` | `docker compose exec itinerary-postgres ...` |
> | `docker logs api-gateway` / `docker logs send-notification-function` | `docker compose logs api-gateway` / `docker compose logs send-notification-function` |
> | Logs del relay y del trigger en su terminal | `docker compose logs -f outbox-relay event-trigger` |
> | `python -m app.replay_dlq` | `docker compose run --rm event-trigger python -m app.replay_dlq` |
>
> Los `curl` no cambian.

Las solicitudes entran por el gateway
(`http://localhost:8000/api/itineraries`), igual que lo hará el frontend. Los comandos se ejecutan desde `serverless\event-trigger` y son **iguales en
PowerShell y CMD** (en CMD, ejecutar antes `chcp 65001` para ver bien las tildes). En la Terminal de macOS (zsh) los
`docker exec` y `python -m ...` son iguales; los `curl` tienen su propio bloque (`curl` en lugar de `curl.exe` y la
ruta del archivo con `/`). El cuerpo del itinerario está en `demo\create-itinerary.json`; si la fecha `2026-12-15` ya
pasó, cámbiala por una futura.

### 1. Caso normal

```
curl.exe -s -X POST http://localhost:8000/api/itineraries -H "Content-Type: application/json" -H "X-Correlation-ID: demo-e2e" --data-binary "@demo\create-itinerary.json"
```

**macOS (zsh):**

```bash
curl -s -X POST http://localhost:8000/api/itineraries -H "Content-Type: application/json" -H "X-Correlation-ID: demo-e2e" --data-binary "@demo/create-itinerary.json"
```

Resultado esperado:

- El gateway devuelve el **201** de Itinerary Service con el itinerario, y el header `X-Correlation-ID: demo-e2e`.
- `docker logs api-gateway` muestra la solicitud con `upstream_status=201 correlation_id=demo-e2e`.
- Unos segundos después, el log del relay muestra `1 publicados` y el del trigger,
  `Evento procesado (PROCESSED): event_id=<id>. ACK`.
- `docker logs send-notification-function` muestra `Correo simulado enviado a ana@example.com: Hola Ana Pérez...`.

El registro en el historial, con el mismo `correlation_id` que llegó al gateway (la trazabilidad empieza en el gateway):

```
docker exec notification-postgres psql -U notification -d notification_db -c "SELECT event_id, status, recipient, correlation_id, processed_at FROM notification_history ORDER BY processed_at DESC LIMIT 3;"
```

Y en la outbox, el evento ya publicado:

```
docker exec itinerary-postgres psql -U itinerary -d itinerary_db -c "SELECT id, published_at, attempts FROM outbox_events ORDER BY occurred_at DESC LIMIT 1;"
```

**Sin `X-Correlation-ID`:** repetir el `POST` sin ese header. El gateway genera uno con forma de UUID, lo devuelve en
el header `X-Correlation-ID` de la respuesta, y ese mismo valor aparece en el log del relay y en `notification_history`.

### 2. Evento duplicado

La entrega es "al menos una vez": si el relay se cae entre publicar y marcar `published_at`, publica el evento otra
vez. Se simula quitando la marca del último evento:

```
docker exec itinerary-postgres psql -U itinerary -d itinerary_db -c "UPDATE outbox_events SET published_at = NULL WHERE id = (SELECT id FROM outbox_events ORDER BY occurred_at DESC LIMIT 1);"
```

Resultado esperado:

- El relay lo publica otra vez y el trigger registra `Evento procesado (ALREADY_PROCESSED): event_id=<el mismo id>. ACK`.
- La consulta del historial sigue mostrando **una sola fila** para ese `event_id`: la función es idempotente.
- No hay un segundo correo simulado en los logs de la función.

### 3. Evento que termina en la DLQ y su reprocesamiento

Un evento válido termina en la DLQ cuando falla el despliegue. Se simula la **migración del historial sin aplicar**
renombrando la tabla, sin borrar su contenido:

```
docker exec notification-postgres psql -U notification -d notification_db -c "ALTER TABLE notification_history RENAME TO notification_history_respaldo;"
curl.exe -s -X POST http://localhost:8000/api/itineraries -H "Content-Type: application/json" -H "X-Correlation-ID: demo-dlq" --data-binary "@demo\create-itinerary.json"
```

**macOS (zsh):** el mismo `docker exec` y después:

```bash
curl -s -X POST http://localhost:8000/api/itineraries -H "Content-Type: application/json" -H "X-Correlation-ID: demo-dlq" --data-binary "@demo/create-itinerary.json"
```

Resultado esperado: el trigger hace 3 intentos con `errorType=ProgrammingError: ... relation "notification_history"
does not exist` y registra `Error de la función en 3 intentos ... Va a la DLQ`. En el panel
(http://localhost:15672 → *Queues and Streams*), `notification.itinerary-created.dlq` tiene 1 mensaje.

Ahora se **corrige la causa** (la tabla vuelve a existir) y se **reprocesa** el mensaje:

```
docker exec notification-postgres psql -U notification -d notification_db -c "ALTER TABLE notification_history_respaldo RENAME TO notification_history;"
python -m app.replay_dlq
```

Resultado esperado:

- El comando registra `Mensaje devuelto de la DLQ a la cola notification.itinerary-created: message_id=<event_id> motivo del rechazo=rejected ...`.
- El trigger registra `Evento procesado (PROCESSED) ... ACK`.
- La DLQ queda en 0 y el historial tiene la fila con `correlation_id = demo-dlq`.

### 4. Evento inválido en la DLQ (no se reprocesa)

Itinerary Service solo produce eventos válidos, así que se publica uno a mano con la API del panel de RabbitMQ:

```
curl.exe -s -u guest:guest -X POST http://localhost:15672/api/exchanges/%2F/itinerary.events/publish -H "Content-Type: application/json" --data-binary "@demo\publish-invalid-event.json"
```

**macOS (zsh):**

```bash
curl -s -u guest:guest -X POST http://localhost:15672/api/exchanges/%2F/itinerary.events/publish -H "Content-Type: application/json" --data-binary "@demo/publish-invalid-event.json"
```

Resultado esperado: el trigger registra `La función rechazó el evento (fallo permanente) ... Va a la DLQ`, sin
reintentos. Este mensaje **no** se reprocesa: no cumple el contrato y volvería a la DLQ. Con
`demo\publish-not-json.json` se ve el mismo resultado para un mensaje que no es JSON, sin que se invoque la función.

### Ver en qué cola está cada mensaje

En http://localhost:15672 (usuario y clave `guest`) → **Queues and Streams**:

- `notification.itinerary-created`: *Ready* (esperando al trigger), *Unacked* (procesándose o reintentándose) y
  *Consumers* (1 si el trigger está conectado).
- `notification.itinerary-created.dlq`: mensajes apartados. En **Get messages** con *Ack mode: Nack message requeue
  true* se ven sin sacarlos; el header `x-death` dice de qué cola vinieron y el motivo.

Más escenarios (función apagada, base de datos de notificaciones apagada, trigger apagado desde el principio) en
[`serverless/event-trigger/README.md`](serverless/event-trigger/README.md) y en ADR-031.

## Pruebas

| Nivel | Componente | Pruebas | Necesita |
|---|---|---|---|
| Unitarias, integración y contrato | `services/airport-service` | 203 | Nada (Redis opcional) |
| Unitarias, integración y contrato | `services/itinerary-service` | 195 | PostgreSQL y RabbitMQ para las de integración |
| Unitarias, integración y contrato | `serverless/send-notification-function` | 70 | PostgreSQL para las de integración |
| Unitarias e integración | `serverless/event-trigger` | 86 | RabbitMQ y la función para las de integración |
| Paquete compartido | `libs/observability` | 18 | Nada |
| Configuración de Nginx | `gateway` | 53 | Docker (y el gateway real para 3 *smoke*) |
| Punta a punta | `tests/e2e` | 14 | El sistema con el simulador (abajo) |

Sin los servicios, las pruebas de integración quedan **SKIPPED** (no fallan). Las de integración usan bases propias
(`itinerary_db_test`, `notification_db_test`) y colas con nombres `test-<id>.`: se pueden correr durante una
demostración sin perder datos.

Cada componente se prueba desde su carpeta, con su entorno virtual activado (CLAUDE.md 4.3; en la función el archivo es
`requirements-dev.txt`, igual que en `libs/observability`). El comando es igual en PowerShell, CMD y zsh:

```
pytest -v
```

**Pruebas de punta a punta.** Levantan el sistema completo con el simulador de API Colombia (sin internet):

PowerShell y CMD:

```powershell
docker compose -f docker-compose.yml -f docker-compose.e2e.yml up -d --build --wait
cd tests\e2e
py -3.12 -m venv .venv
.venv\Scriptsctivate
pip install -r requirements.txt
pytest -v
```

macOS (zsh):

```bash
docker compose -f docker-compose.yml -f docker-compose.e2e.yml up -d --build --wait
cd tests/e2e
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -v
```

(En PowerShell, `.venv\Scripts\Activate.ps1` en lugar de `activate`.) Para volver a usar la API Colombia real:
`docker compose up -d` (sin el segundo archivo) recrea Airport Service con la dirección real.

**Contrato de Airport Service.** Si cambias su API a propósito, regenera `docs/openapi/airport-service.json` desde
`services/airport-service` y revisa el diff: `$env:UPDATE_CONTRACTS = "1"; pytest tests/test_openapi_contract.py`
(PowerShell), `set UPDATE_CONTRACTS=1 && pytest tests/test_openapi_contract.py` (CMD) o
`UPDATE_CONTRACTS=1 pytest tests/test_openapi_contract.py` (zsh).

## Desarrollo

El desarrollo sigue un enfoque incremental. Cada fase incluye explicación, estructura de archivos, implementación cuando corresponda, instrucciones de ejecución, pruebas y una lista de verificación.

El flujo de trabajo del equipo (issues, ramas, commits, pull requests y revisión) está en [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Ramas del repositorio

**La versión integrada y vigente del sistema está siempre en `main`.** Las demás ramas son de consulta.

| Rama | Contenido | Etiqueta |
|---|---|---|
| `main` | Todas las fases fusionadas: versión vigente | — |
| `fase-1-airport-service` | Fase 1 — Airport Service. La rama se borró con la regla anterior; su estado se conserva en la etiqueta | `fase-1` |
| `fase-2-resiliencia` | Fase 2 — Resiliencia y caché. La rama se borró con la regla anterior; su estado se conserva en la etiqueta | `fase-2` |
| `fase-3-itinerary-service` | Fase 3 — Itinerary Service (CRUD, PostgreSQL, Alembic, validación de aeropuertos) | `fase-3` |
| `fase-4-eventos-rabbitmq` | Fase 4 — `ItineraryCreatedEvent`, RabbitMQ y AsyncAPI | `fase-4` |
| `fase-5-transactional-outbox` | Fase 5 — Transactional Outbox, Outbox Relay y mensajes venenosos | `fase-5` |
| `fase-6-serverless` | Fase 6 — SendNotificationFunction (AWS Lambda + RIE), Event Trigger, DLQ y su reprocesamiento | `fase-6` |
| `fase-7-api-gateway` | Fase 7 — API Gateway con Nginx (enrutamiento, rate limiting, correlation ID, propagación de `Authorization`) | `fase-7` |
| `fase-8-frontend` | Fase 8 — Frontend (mapa con Plotly JS, CRUD de itinerarios, estáticos servidos por Nginx) | `fase-8` |
| `fase-9-observabilidad` | Fase 9 — Observabilidad (logs JSON, OpenTelemetry y Jaeger, Prometheus y Grafana, `libs/observability`) | `fase-9` |
| `fase-10-docker-compose` | Fase 10 — Docker y Docker Compose (imágenes de todos los componentes, migraciones automáticas, orden de arranque) | `fase-10` (al fusionar) |

- Cada rama `fase-N-...` se **conserva después del merge como archivo de solo lectura**: muestra los commits de cada entrega de esa fase. No se trabaja en ellas después de fusionarlas; cualquier corrección sale de una rama nueva desde `main`.
- Las ramas auxiliares (`chore/`, `fix/`, `docs/`) se borran después del merge.
- Cada etiqueta `fase-N` apunta al commit del merge de esa fase en `main`. Para ver el sistema tal como quedó al cerrar una fase: `git switch --detach fase-3`.

## Uso de Claude Code

El equipo usa [Claude Code](https://claude.com/claude-code) como herramienta de desarrollo (asistente de programación). Las reglas que sigue en este repositorio están en [`CLAUDE.md`](CLAUDE.md), y cada cambio que propone lo revisa, confirma y sube un integrante del equipo, que es el autor del commit.

Los commits y las descripciones de pull request **no llevan la línea de coautoría** de Claude (`Co-Authored-By`); está desactivada en `.claude/settings.json`. Los commits de la Fase 3 sí la conservan porque son anteriores a esta regla, y el equipo decidió no volver a reescribir el historial de `main`.

## Contexto académico

Proyecto universitario para la asignatura Arquitecturas de Software Emergentes.
