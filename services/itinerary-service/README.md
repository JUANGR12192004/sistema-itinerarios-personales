# Itinerary Service

Microservicio de gestión de itinerarios de viaje. Permite crear, consultar, actualizar y eliminar itinerarios entre aeropuertos colombianos. Valida que los aeropuertos existan consultando Airport Service antes de guardar.

Cada itinerario creado origina un `ItineraryCreatedEvent`. El servicio lo guarda en la tabla `outbox_events` en la **misma transacción** que el itinerario (Transactional Outbox, Fase 5), y un proceso aparte, el **Outbox Relay**, lo publica en RabbitMQ.

## Requisitos previos

- Python 3.12 (`py -3.12` en Windows, `python3.12` en macOS)
- Docker Desktop (para PostgreSQL y RabbitMQ)
- Airport Service corriendo en `http://localhost:8001`
- RabbitMQ (Docker) para que el Outbox Relay publique los eventos. Sin RabbitMQ la API funciona igual: los eventos quedan pendientes en `outbox_events` y se publican cuando RabbitMQ vuelve

## Configuración inicial (una vez por equipo)

```powershell
# Permitir activar entornos virtuales (solo PowerShell; no aplica en CMD ni en macOS)
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

## Instalación

**PowerShell:**

```powershell
cd services\itinerary-service
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**CMD:**

```cmd
cd services\itinerary-service
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**macOS (zsh):**

```bash
cd services/itinerary-service
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Base de datos PostgreSQL

Levantar el contenedor (solo la primera vez; después basta con `docker start itinerary-postgres`).

**PowerShell:**

```powershell
docker run -d --name itinerary-postgres `
  -e POSTGRES_USER=itinerary `
  -e POSTGRES_PASSWORD=itinerary `
  -e POSTGRES_DB=itinerary_db `
  -p 5433:5432 `
  postgres:16-alpine
```

**CMD y macOS (zsh):**

```cmd
docker run -d --name itinerary-postgres -e POSTGRES_USER=itinerary -e POSTGRES_PASSWORD=itinerary -e POSTGRES_DB=itinerary_db -p 5433:5432 postgres:16-alpine
```

Aplicar las migraciones (con el entorno virtual activado; igual en PowerShell, CMD y zsh):

```powershell
alembic upgrade head
alembic current
```

`alembic current` debe mostrar `c4d8e2f6a9b1 (head)`. Las migraciones son:

| Revisión | Contenido |
|---|---|
| `a3f1e2b4c5d0` | Tabla `itineraries` (Fase 3) |
| `b7c2d9e1f4a6` | Tabla `outbox_events` con el índice parcial de pendientes (Fase 5, ADR-024) |
| `c4d8e2f6a9b1` | Columna `failed_at` para los mensajes venenosos (Fase 5, ADR-027) |

Cada integrante debe correr `alembic upgrade head` después de traer cambios con migraciones nuevas.

## Variables de entorno

Copia `.env.example` a `.env` y ajusta los valores si es necesario (igual en PowerShell y CMD):

```powershell
copy .env.example .env
```

En macOS (zsh): `cp .env.example .env`.

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `DATABASE_URL` | Sin valor por defecto (**obligatoria**). En `.env.example`: `postgresql+psycopg://itinerary:itinerary@localhost:5433/itinerary_db` | Conexión a PostgreSQL. Las pruebas no la necesitan: `tests/conftest.py` usa una URL de prueba si no está definida |
| `DATABASE_CONNECT_TIMEOUT_SECONDS` | `5` | Tiempo máximo para abrir una conexión a PostgreSQL (segundos enteros, mínimo 2) |
| `AIRPORT_SERVICE_URL` | `http://localhost:8001` | URL de Airport Service |
| `AIRPORT_SERVICE_TIMEOUT_SECONDS` | `5.0` | Timeout en segundos para llamadas a Airport Service |
| `RABBITMQ_URL` | `amqp://localhost:5672/%2F` (usuario `guest`) | Conexión a RabbitMQ (la usa el Outbox Relay) |
| `RABBITMQ_TIMEOUT_SECONDS` | `3.0` | Timeout para conectar y publicar en RabbitMQ |
| `OUTBOX_RELAY_POLL_INTERVAL_SECONDS` | `2.0` | Pausa del Outbox Relay entre revisiones de la outbox |
| `OUTBOX_RELAY_BATCH_SIZE` | `10` | Máximo de eventos pendientes que el relay toma por ciclo |
| `LOG_LEVEL` | `INFO` | Nivel de logging |

## RabbitMQ

Hasta la Fase 10 (Docker Compose), RabbitMQ se ejecuta con un contenedor (igual en PowerShell, CMD y zsh):

```powershell
docker run -d --name itinerary-rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.13-management
```

- Puerto `5672`: protocolo AMQP (lo usa el Outbox Relay).
- Puerto `15672`: panel web en http://localhost:15672 (usuario y clave `guest`, solo para desarrollo local).
- No hace falta crear nada a mano. Desde la Fase 6 (ADR-032) cada lado declara lo suyo: el publicador
  declara el exchange `itinerary.events` y el Event Trigger (`serverless/event-trigger`) declara la cola,
  su enlace, la DLX y la DLQ. Si el trigger todavía no ha arrancado, la cola no existe: el relay registra
  un fallo temporal y el evento **espera en la outbox** hasta que el trigger arranque.
- RabbitMQ tarda unos segundos en arrancar. Está listo cuando `docker logs itinerary-rabbitmq` muestra
  `Server startup complete`. No uses `docker exec ... rabbitmq-diagnostics` mientras arranca: puede crear el
  archivo `.erlang.cookie` con el dueño equivocado y el contenedor se detiene con el error `eacces`.

| Elemento | Nombre |
|---|---|
| Exchange | `itinerary.events` (topic, durable) |
| Routing key | `itinerary.created` |
| Cola | `notification.itinerary-created` (durable) |
| Dead letter exchange / cola | `itinerary.events.dlx` / `notification.itinerary-created.dlq` |

El contrato del evento está en [`docs/asyncapi/asyncapi.yaml`](../../docs/asyncapi/asyncapi.yaml)
y la explicación completa (Outbox, duplicados, idempotencia y mensajes venenosos) en
[`docs/04-comunicacion-y-eventos.md`](../../docs/04-comunicacion-y-eventos.md).

## Orden de arranque del sistema completo

Itinerary Service ocupa los pasos **5** (API) y **6** (Outbox Relay) del orden completo, explicado en el
[README raíz](../../README.md#orden-de-arranque):

1. Contenedores (`itinerary-postgres`, `itinerary-rabbitmq`, `notification-postgres` y la red `notification-net`).
2. Migraciones: `itinerary_db` (**este servicio**, `alembic upgrade head`) y `notification_db`.
3. SendNotificationFunction.
4. Airport Service.
5. **API de Itinerary Service.**
6. **Outbox Relay.**
7. Event Trigger.
8. API Gateway (contenedor `api-gateway`, puerto 8000).

| Paso omitido | Consecuencia |
|---|---|
| `itinerary-postgres` apagado | `POST /itineraries` responde 500 `INTERNAL_ERROR`; el relay registra un error en cada ciclo y sigue |
| Migración de `itinerary_db` sin aplicar | `POST /itineraries` responde 500 (la tabla no existe) |
| Airport Service apagado | `POST /itineraries` responde 503 `AIRPORT_SERVICE_UNAVAILABLE` y no se guarda nada |
| Outbox Relay apagado | Los itinerarios se crean (201), pero sus eventos se acumulan pendientes en la outbox hasta que arranque |
| RabbitMQ apagado, o Event Trigger que nunca arrancó (la cola no existe) | El relay registra un fallo temporal (`EventPublishError` o `UnroutableError`) y el evento **espera en la outbox** hasta que se resuelva |

## Ejecución

El servicio tiene **dos procesos**. Cada uno va en su propia terminal, con el entorno virtual activado.

**1. API REST** (puerto 8002):

```powershell
cd services\itinerary-service
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

```cmd
cd services\itinerary-service
.venv\Scripts\activate.bat
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

```bash
cd services/itinerary-service
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

Swagger UI disponible en: `http://localhost:8002/docs`

**2. Outbox Relay** (publica en RabbitMQ los eventos pendientes):

```powershell
cd services\itinerary-service
.\.venv\Scripts\Activate.ps1
python -m app.outbox_relay
```

```cmd
cd services\itinerary-service
.venv\Scripts\activate.bat
python -m app.outbox_relay
```

```bash
cd services/itinerary-service
source .venv/bin/activate
python -m app.outbox_relay
```

Muestra `Outbox Relay iniciado: revisa cada 2.0 s, lotes de hasta 10 eventos` y se detiene con **Ctrl+C**.
Si PostgreSQL o RabbitMQ no están disponibles, registra el error y lo vuelve a intentar en el siguiente ciclo:
el proceso no se detiene.

## Pruebas

Con el entorno virtual activado (igual en PowerShell y CMD; en zsh, las carpetas con `/`, por ejemplo
`pytest -v tests/integration`):

```powershell
# Todas las pruebas (las de integración se omiten si PostgreSQL o RabbitMQ no están disponibles)
pytest -v

# Solo pruebas unitarias y de API (sin PostgreSQL ni RabbitMQ)
pytest -v tests\domain tests\application tests\infrastructure tests\api tests\test_config.py tests\test_outbox_relay_process.py

# Solo pruebas de integración (requieren PostgreSQL con `alembic upgrade head`, y RabbitMQ)
pytest -v tests\integration
```

Resultado esperado: **169 passed** con PostgreSQL y RabbitMQ; **144 passed, 25 skipped** sin ellos.

**RabbitMQ:** las pruebas de integración **no tocan** la cola real `notification.itinerary-created` ni su DLQ.
Usan una topología propia con nombres únicos (`test-<id>.itinerary.events`, `test-<id>.notification.itinerary-created`,
etc.), declarada una vez por sesión de pytest y **borrada al terminar** (mismo criterio que las pruebas del Event
Trigger). Se pueden correr durante una demostración sin perder los mensajes que esperan en la cola o en la DLQ.

> **Limitación (base de datos):** las pruebas de integración usan la base real `itinerary_db` y **borran** las filas
> de `itineraries` y `outbox_events` antes y después de cada prueba. Además, si el **Outbox Relay** está encendido,
> puede publicar en la cola real los eventos que crean las pruebas. Antes de correrlas, detén el Outbox Relay y no
> las ejecutes contra datos de demostración que quieras conservar. Está registrado como pendiente en `CLAUDE.md`
> (sección 9.3).

## Endpoints

| Método | Ruta | Descripción | Éxito |
|---|---|---|---|
| `POST` | `/itineraries` | Crear itinerario (y registrar su evento en la outbox) | 201 |
| `GET` | `/itineraries` | Listar todos | 200 |
| `GET` | `/itineraries/{id}` | Obtener por ID | 200 |
| `PUT` | `/itineraries/{id}` | Actualizar | 200 |
| `DELETE` | `/itineraries/{id}` | Eliminar | 204 |
| `GET` | `/health` | Estado del servicio | 200 |

## Demostración: double write resuelto con el Transactional Outbox (Fase 5)

En la Fase 4, si RabbitMQ estaba caído al crear un itinerario, la API respondía 201 pero el evento **se perdía**
(*double write*: dos escrituras en sistemas distintos sin una transacción común). Esta demostración repite el
mismo experimento y muestra que ahora el evento **espera** en la outbox y se publica cuando RabbitMQ vuelve.

Requisitos: PostgreSQL y RabbitMQ creados (secciones anteriores), migraciones aplicadas, Airport Service en el
puerto 8001 y la API de Itinerary Service en el 8002. **No** arranques todavía el Outbox Relay.
Si la fecha `2026-12-15` ya pasó, cámbiala por una futura.

### 1. Detener RabbitMQ y crear un itinerario

**PowerShell:**

```powershell
docker stop itinerary-rabbitmq

$body = @{
  traveler_name        = "Ana Perez"
  traveler_email       = "ana@example.com"
  departure_airport_id = 1
  arrival_airport_id   = 5
  travel_date          = "2026-12-15T08:00:00-05:00"
  duration_minutes     = 75
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8002/itineraries `
  -ContentType "application/json" -Headers @{ "X-Correlation-ID" = "demo-fase-5" } -Body $body
```

**CMD:**

```cmd
docker stop itinerary-rabbitmq
chcp 65001
curl.exe -s -X POST http://localhost:8002/itineraries -H "Content-Type: application/json" -H "X-Correlation-ID: demo-fase-5" -d "{\"traveler_name\":\"Ana Perez\",\"traveler_email\":\"ana@example.com\",\"departure_airport_id\":1,\"arrival_airport_id\":5,\"travel_date\":\"2026-12-15T08:00:00-05:00\",\"duration_minutes\":75}"
```

**macOS (zsh):**

```bash
docker stop itinerary-rabbitmq
curl -s -X POST http://localhost:8002/itineraries -H "Content-Type: application/json" -H "X-Correlation-ID: demo-fase-5" -d '{"traveler_name":"Ana Perez","traveler_email":"ana@example.com","departure_airport_id":1,"arrival_airport_id":5,"travel_date":"2026-12-15T08:00:00-05:00","duration_minutes":75}'
```

Resultado esperado:

- La API responde **201** con el itinerario, aunque RabbitMQ esté detenido: la API ya no habla con RabbitMQ.
- El log de la API muestra `Itinerario creado: id=<id>, evento itinerary.created registrado (event_id=<event_id>)`.
- Ya no aparece `Evento perdido`.

### 2. Ver el evento pendiente en la outbox

Igual en PowerShell, CMD y zsh:

```powershell
docker exec itinerary-postgres psql -U itinerary -d itinerary_db -c "SELECT id, event_type, published_at, attempts, failed_at FROM outbox_events"
```

Resultado esperado: una fila con `event_type = itinerary.created`, `published_at` vacío (**pendiente**) y
`attempts = 0`. El `id` de la fila es el `event_id` del log.

### 3. Arrancar el Outbox Relay con RabbitMQ todavía detenido

En otra terminal, con el entorno virtual activado (igual en PowerShell, CMD y zsh):

```powershell
python -m app.outbox_relay
```

Resultado esperado: cada 2 segundos el relay intenta publicar y falla, sin perder el evento:

```
WARNING app.application.outbox_relay: No se pudo publicar el evento <event_id> (intento 1): No se pudo conectar con RabbitMQ en localhost:5672. Se detiene el lote; se reintenta en el siguiente ciclo
INFO app.application.outbox_relay: Ciclo del Outbox Relay: 0 publicados, 1 fallidos (se reintentan), 0 descartados
```

Si repites la consulta del paso 2, `attempts` crece y `last_error` guarda el motivo, pero `published_at`
sigue vacío: el evento sigue pendiente.

### 4. Volver a levantar RabbitMQ

En la primera terminal (igual en PowerShell, CMD y zsh):

```powershell
docker start itinerary-rabbitmq
```

Unos segundos después, cuando RabbitMQ termina de arrancar, el log del relay muestra:

```
INFO app.infrastructure.messaging.rabbitmq_event_publisher: Evento publicado: itinerary.created event_id=<event_id> itinerary_id=<id> correlation_id=demo-fase-5
INFO app.application.outbox_relay: Ciclo del Outbox Relay: 1 publicados, 0 fallidos (se reintentan), 0 descartados
```

### 5. Ver el evento en la cola

Desde la Fase 6 la cola `notification.itinerary-created` la declara el Event Trigger (ADR-032). Si el trigger nunca
arrancó, la cola no existe y el relay del paso 4 registra `UnroutableError` en lugar de publicar: el evento sigue
esperando en la outbox. Arranca el trigger una vez (`python -m app.main` en `serverless\event-trigger`) y detenlo
con Ctrl+C antes de este paso si quieres ver el mensaje en la cola; con el trigger encendido, el mensaje se procesa
enseguida y la cola queda vacía.

Leer el mensaje sin sacarlo de la cola (API del panel de RabbitMQ).

**PowerShell:**

```powershell
curl.exe -s -u guest:guest -H "Content-Type: application/json" `
  -X POST http://localhost:15672/api/queues/%2F/notification.itinerary-created/get `
  -d '{\"count\":1,\"ackmode\":\"ack_requeue_true\",\"encoding\":\"auto\"}'
```

**CMD:**

```cmd
curl.exe -s -u guest:guest -H "Content-Type: application/json" -X POST http://localhost:15672/api/queues/%2F/notification.itinerary-created/get -d "{\"count\":1,\"ackmode\":\"ack_requeue_true\",\"encoding\":\"auto\"}"
```

**macOS (zsh):**

```bash
curl -s -u guest:guest -H "Content-Type: application/json" \
  -X POST http://localhost:15672/api/queues/%2F/notification.itinerary-created/get \
  -d '{"count":1,"ackmode":"ack_requeue_true","encoding":"auto"}'
```

Resultado esperado:

- El `payload` es el evento, con `"event_type": "itinerary.created"`, el mismo `itinerary_id` y `"correlation_id": "demo-fase-5"`.
- Las propiedades traen `message_id` igual al `event_id` (clave de idempotencia del consumidor) y `delivery_mode` = 2 (persistente).
- También se ve en el panel: **Queues and Streams → notification.itinerary-created → Get messages**.
- En la outbox (consulta del paso 2), la fila tiene ahora `published_at` con fecha.

**Conclusión:** el itinerario y su evento se guardaron en la misma transacción. RabbitMQ estuvo caído durante
la creación y durante varios ciclos del relay, y aun así el evento llegó a la cola. Eso es el double write resuelto.

### Lo que queda por cuenta del consumidor

El relay publica y **después** marca `published_at`. Si se detiene justo entre esos dos pasos, el evento se
publicará otra vez (entrega **al menos una vez**). Por eso el consumidor de la Fase 6 debe ser **idempotente**
con `event_id`. La prueba `test_si_el_relay_cae_antes_del_commit_el_evento_se_publica_dos_veces` lo demuestra.
Los mensajes ilegibles de la outbox se descartan con `failed_at` y no se reintentan (ADR-027).
Detalles: [`docs/04-comunicacion-y-eventos.md`](../../docs/04-comunicacion-y-eventos.md), sección 7.

## Estructura

```
app/
  domain/              → Itinerary (agregado), reglas de negocio, excepciones
  application/         → Puertos, casos de uso, excepciones de aplicación
    events.py          → ItineraryCreatedEvent (contrato de integración v1)
    outbox.py          → OutboxMessage (mensaje pendiente de la outbox)
    outbox_relay.py    → OutboxRelay: publica los pendientes (lógica, sin infraestructura)
  infrastructure/
    persistence/       → Repositorios SQLAlchemy, modelos ORM, Unit of Work,
                         OutboxEventPublisher (guarda el evento) y SqlAlchemyOutboxRepository
    airport_client/    → HttpAirportCatalogAdapter (llama a Airport Service)
    messaging/         → RabbitMQEventPublisher y topología de RabbitMQ (los usa el relay)
  api/                 → Rutas, esquemas Pydantic, manejador de errores, dependencias
  main.py              → Creación de la app FastAPI
  outbox_relay.py      → Proceso del Outbox Relay (python -m app.outbox_relay)
alembic/               → Migraciones de base de datos
tests/
  domain/              → Pruebas de dominio (sin dependencias externas)
  application/         → Casos de uso, evento, OutboxMessage y OutboxRelay con fakes
  infrastructure/      → HttpAirportCatalogAdapter (respx), RabbitMQEventPublisher y OutboxEventPublisher
  integration/         → Pruebas contra PostgreSQL y RabbitMQ reales (SKIPPED en CI)
  api/                 → Pruebas de rutas con fakes inyectados
```
