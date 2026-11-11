
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
5. **API Gateway / BFF:** punto de entrada para las solicitudes del frontend.
6. **Frontend:** interfaz de gestión de itinerarios y visualización de aeropuertos.

La implementación se desarrolla progresivamente, siguiendo las fases definidas en la documentación del proyecto.

## Tecnologías

| Área | Tecnología |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic |
| Persistencia | PostgreSQL (una base por servicio) |
| ORM y migraciones | SQLAlchemy y Alembic |
| Comunicación síncrona | HTTP / REST |
| Mensajería | RabbitMQ (pika) |
| Caché | Redis |
| Serverless | Imagen oficial de AWS Lambda para Python 3.12 con el Runtime Interface Emulator (ADR-008) |
| Frontend | HTML, CSS, JavaScript |
| Visualización | Plotly JS |
| Contenedores | Docker y Docker Compose |
| Observabilidad | OpenTelemetry, Jaeger, Prometheus y Grafana |
| Documentación API | Swagger / OpenAPI y AsyncAPI |
| Pruebas | pytest, TestClient de FastAPI y respx |

## Arquitectura

El sistema utiliza microservicios con responsabilidades delimitadas, comunicación HTTP para las operaciones que necesitan una respuesta inmediata y mensajería asíncrona para los eventos de integración.

Cada microservicio de negocio tiene su propia base de datos y es responsable de sus propios datos.

Se aplican arquitectura hexagonal, el patrón Adapter y conceptos de DDD para mantener separadas las reglas de negocio y los detalles de infraestructura.

```mermaid
flowchart LR
    C[Cliente] -->|POST /itineraries| IS[Itinerary Service :8002]
    IS -->|"HTTP: validar aeropuertos"| AS[Airport Service :8001]
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
| 6 | Serverless | En revisión (rama `fase-6-serverless`) |
| 7 a 12 | Gateway, frontend, observabilidad, Docker Compose, pruebas y documentación | Pendientes |

**Fase actual:** Fase 6 — Serverless. Implementada en la rama `fase-6-serverless`, pendiente de pull request y merge.

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

## Orden de arranque

Hasta la Fase 10 (Docker Compose) el sistema se levanta a mano. El orden importa porque cada paso necesita los
anteriores. La instalación de cada componente (entorno virtual, `.env`) está en su README; aquí está el orden para
levantarlo todo.

### 1. Contenedores

Igual en PowerShell y CMD. **La primera vez** se crean:

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

### 2. Migraciones

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

### 3. SendNotificationFunction

Igual en PowerShell y CMD, desde `serverless\send-notification-function`. La primera vez (y después de cada cambio en
el código de la función) se construye la imagen y se crea el contenedor:

```
docker build -t send-notification-function .
docker run -d --name send-notification-function --network notification-net -p 9000:8080 -e DATABASE_URL=postgresql+psycopg://notification:notification@notification-postgres:5432/notification_db send-notification-function
```

Las veces siguientes: `docker start send-notification-function`.

### 4 a 7. Procesos de Python

Cada uno en **su propia terminal**, con el entorno virtual de su carpeta activado
(`.\.venv\Scripts\Activate.ps1` en PowerShell, `.venv\Scripts\activate.bat` en CMD). Los comandos son iguales en las
dos terminales:

| Paso | Carpeta | Comando | Listo cuando |
|---|---|---|---|
| 4. Airport Service | `services\airport-service` | `uvicorn app.main:app --port 8001` | http://localhost:8001/health responde |
| 5. Itinerary Service | `services\itinerary-service` | `uvicorn app.main:app --port 8002` | http://localhost:8002/health responde |
| 6. Outbox Relay | `services\itinerary-service` | `python -m app.outbox_relay` | `Outbox Relay iniciado` |
| 7. Event Trigger | `serverless\event-trigger` | `python -m app.main` | `escuchando la cola notification.itinerary-created` |

Para detener todo: Ctrl+C en cada terminal y `docker stop send-notification-function notification-postgres itinerary-rabbitmq itinerary-postgres airport-redis`.

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

## Demostración de punta a punta

Recorrido completo: crear un itinerario → outbox → relay → RabbitMQ → trigger → función → historial. Requisitos: los
siete pasos del orden de arranque. Los comandos se ejecutan desde `serverless\event-trigger` y son **iguales en
PowerShell y CMD** (en CMD, ejecutar antes `chcp 65001` para ver bien las tildes). El cuerpo del itinerario está en
`demo\create-itinerary.json`; si la fecha `2026-12-15` ya pasó, cámbiala por una futura.

### 1. Caso normal

```
curl.exe -s -X POST http://localhost:8002/itineraries -H "Content-Type: application/json" -H "X-Correlation-ID: demo-e2e" --data-binary "@demo\create-itinerary.json"
```

Resultado esperado:

- La API responde **201** con el itinerario.
- Unos segundos después, el log del relay muestra `1 publicados` y el del trigger,
  `Evento procesado (PROCESSED): event_id=<id>. ACK`.
- `docker logs send-notification-function` muestra `Correo simulado enviado a ana@example.com: Hola Ana Pérez...`.

El registro en el historial (con el mismo `correlation_id`):

```
docker exec notification-postgres psql -U notification -d notification_db -c "SELECT event_id, status, recipient, correlation_id, processed_at FROM notification_history ORDER BY processed_at DESC LIMIT 3;"
```

Y en la outbox, el evento ya publicado:

```
docker exec itinerary-postgres psql -U itinerary -d itinerary_db -c "SELECT id, published_at, attempts FROM outbox_events ORDER BY occurred_at DESC LIMIT 1;"
```

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
curl.exe -s -X POST http://localhost:8002/itineraries -H "Content-Type: application/json" -H "X-Correlation-ID: demo-dlq" --data-binary "@demo\create-itinerary.json"
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

- Cada rama `fase-N-...` se **conserva después del merge como archivo de solo lectura**: muestra los commits de cada entrega de esa fase. No se trabaja en ellas después de fusionarlas; cualquier corrección sale de una rama nueva desde `main`.
- Las ramas auxiliares (`chore/`, `fix/`, `docs/`) se borran después del merge.
- Cada etiqueta `fase-N` apunta al commit del merge de esa fase en `main`. Para ver el sistema tal como quedó al cerrar una fase: `git switch --detach fase-3`.

## Uso de Claude Code

El equipo usa [Claude Code](https://claude.com/claude-code) como herramienta de desarrollo (asistente de programación). Las reglas que sigue en este repositorio están en [`CLAUDE.md`](CLAUDE.md), y cada cambio que propone lo revisa, confirma y sube un integrante del equipo, que es el autor del commit.

Los commits y las descripciones de pull request **no llevan la línea de coautoría** de Claude (`Co-Authored-By`); está desactivada en `.claude/settings.json`. Los commits de la Fase 3 sí la conservan porque son anteriores a esta regla, y el equipo decidió no volver a reescribir el historial de `main`.

## Contexto académico

Proyecto universitario para la asignatura Arquitecturas de Software Emergentes.
