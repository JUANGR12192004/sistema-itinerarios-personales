# SendNotificationFunction

Función serverless (FaaS) del sistema de notificaciones (Fase 6). Recibe el evento `ItineraryCreatedEvent`, simula
el envío de un correo al viajero y guarda el resultado en su historial, **una sola vez por evento**.

| | |
|---|---|
| Plataforma | Imagen oficial de AWS Lambda `public.ecr.aws/lambda/python:3.12` con el Runtime Interface Emulator (ADR-008) |
| Modelo de programación | `handler(event, context)` en `app/handler.py`, sin estado y sin código de RabbitMQ (ADR-028) |
| Invocación local | `POST http://localhost:9000/2015-03-31/functions/function/invocations` (cuerpo = evento) |
| Historial | PostgreSQL `notification_db`, contenedor `notification-postgres`, puerto 5434, tabla `notification_history` (ADR-029) |
| Idempotencia | `event_id` único: un evento repetido responde `ALREADY_PROCESSED` sin volver a notificar (ADR-030) |
| Quién la invoca | El Event Trigger ([`serverless/event-trigger`](../event-trigger/README.md)), equivalente al Event Source Mapping de AWS |

## ¿Por qué es FaaS si corre en Docker?

Lo que hace FaaS a una función es su **modelo de programación y su contrato con la plataforma**, no el lugar donde
corre. Nuestro código es solo una función `handler(event, context)`: no abre puertos, no tiene servidor web, no conoce
RabbitMQ y no guarda estado entre invocaciones. Quien la ejecuta es la plataforma.

En local, el papel de la plataforma lo hace el **Runtime Interface Emulator** (RIE) que trae la imagen oficial de AWS
Lambda: recibe la invocación por la misma ruta de la API *Invoke* de AWS y llama al handler. La misma imagen se
despliega en AWS Lambda sin cambiar una línea.

En local no hay escalado automático ni apagado cuando no hay eventos: el contenedor es una sola instancia encendida.
Son límites de la plataforma local, no del código (ADR-008).

## Arquitectura hexagonal

| Capa | Archivos | Qué hace |
|---|---|---|
| `domain` | `notification_record.py` | `NotificationRecord` y la regla del destinatario: con correo → `SENT`; sin correo → `SKIPPED` con el motivo |
| `application` | `use_cases.py`, `ports.py`, `events.py`, `exceptions.py` | `NotifyItineraryCreatedUseCase`: insertar si el `event_id` no existe → enviar → commit. Puertos del historial, del envío y de la unidad de trabajo |
| `infrastructure` | `notification/`, `persistence/` | `SimulatedEmailSender` (el correo es una línea de log) y el repositorio con SQLAlchemy. Los errores de conexión a PostgreSQL se convierten en `TransientError` |
| Adaptador de entrada | `handler.py`, `event_schema.py` | El handler de Lambda (como una ruta FastAPI) y el esquema Pydantic del contrato v1 |

## Respuestas de la función

| Respuesta | Cuándo | Qué hace el Event Trigger |
|---|---|---|
| `{"status": "PROCESSED", "notification_status": "SENT" \| "SKIPPED", ...}` | Evento nuevo procesado | ACK |
| `{"status": "ALREADY_PROCESSED", ...}` | El `event_id` ya estaba en el historial | ACK |
| `{"status": "REJECTED", "reason": "..."}` | El evento no cumple el contrato v1 | Lo envía a la DLQ |
| `{"errorType": "TransientError", ...}` | PostgreSQL no disponible | Reintenta sin límite |
| `{"errorType": "<otra clase>", ...}` | Otro error (por ejemplo, falta la migración) | 3 intentos y después a la DLQ |

> El RIE responde **HTTP 200 también cuando la función falla**: el error solo se ve en el cuerpo (`errorType`).
> Si la función supera su timeout (10 s), responde HTTP 200 con el texto `Task timed out after 10.00 seconds`.

## Orden de arranque del sistema completo

La función es el paso **3** del orden completo, que está explicado en el [README raíz](../../README.md#orden-de-arranque):

1. Contenedores (`itinerary-postgres`, `itinerary-rabbitmq`, `notification-postgres` y la red `notification-net`).
2. Migraciones: `itinerary_db` (Itinerary Service) y `notification_db` (**esta función**, `alembic upgrade head`).
3. **La función** (contenedor `send-notification-function`).
4. Airport Service.
5. Itinerary Service.
6. Outbox Relay.
7. Event Trigger.
8. API Gateway (contenedor `api-gateway`, puerto 8000).

Qué pasa si se omite un paso que depende de esta función:

| Paso omitido | Consecuencia |
|---|---|
| `notification-postgres` apagado | La función responde `TransientError`; el trigger reintenta sin límite y nada va a la DLQ. Al encenderlo, se procesa |
| Migración de `notification_db` sin aplicar | La función falla con `ProgrammingError` (la tabla no existe), que **no** es `TransientError`: tras 3 intentos los mensajes van a la **DLQ**. Solución: `alembic upgrade head` y luego `python -m app.replay_dlq --all` en el trigger |
| Contenedor de la función apagado | El trigger no puede conectarse: reintenta sin límite y nada va a la DLQ. Al encenderla, se procesa |

## Instalación (una vez)

Desde `serverless\send-notification-function` (`serverless/send-notification-function` en macOS).

**PowerShell:**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

**CMD:**

```cmd
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
copy .env.example .env
```

**macOS (zsh):**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
cp .env.example .env
```

`requirements.txt` tiene solo lo que va **dentro** de la imagen. `requirements-dev.txt` agrega Alembic y pytest, que
usa el equipo y no van en la imagen (ADR-029).

## Base de datos del historial

Igual en PowerShell, CMD y zsh. La red y el contenedor se crean **una sola vez**:

```
docker network create notification-net
docker run -d --name notification-postgres --network notification-net -p 5434:5432 -e POSTGRES_USER=notification -e POSTGRES_PASSWORD=notification -e POSTGRES_DB=notification_db postgres:16-alpine
```

Las veces siguientes basta con `docker start notification-postgres`.

Aplicar la migración, con el entorno virtual activado (usa `DATABASE_URL` del `.env`, `localhost:5434`):

```
alembic upgrade head
alembic current
```

`alembic current` debe mostrar `d1e5f7a3b9c2 (head)`. Las migraciones se aplican **aparte**, nunca en cada invocación.

## Imagen y ejecución

Igual en PowerShell, CMD y zsh. Construir la imagen (otra vez después de **cada** cambio en `app/`):

```
docker build -t send-notification-function .
```

Ejecutarla en la red `notification-net`, donde la base de datos se llama `notification-postgres` (dentro de un
contenedor, `localhost` es el propio contenedor):

```
docker run -d --name send-notification-function --network notification-net -p 9000:8080 -e DATABASE_URL=postgresql+psycopg://notification:notification@notification-postgres:5432/notification_db send-notification-function
```

En Apple Silicon la imagen se construye para `arm64` (la imagen base de Lambda trae las dos arquitecturas). Para
desplegarla en AWS Lambda habría que crear la función con arquitectura `arm64`, o construirla con
`docker build --platform linux/amd64 -t send-notification-function .`.

Las veces siguientes basta con `docker start send-notification-function`. Para usar una imagen nueva:
`docker rm -f send-notification-function` y repetir el `docker run`. Los logs (incluido el correo simulado) se ven con
`docker logs -f send-notification-function`.

## Invocarla a mano

Desde `serverless\send-notification-function`, igual en PowerShell y CMD (en CMD, ejecutar antes `chcp 65001`).
Los eventos de ejemplo están en `events\`, porque escribir JSON en la línea de comandos cambia entre terminales:

```
curl.exe -s -X POST http://localhost:9000/2015-03-31/functions/function/invocations --data-binary "@events\itinerary-created.json"
```

**macOS (zsh):** `curl` en lugar de `curl.exe` y la ruta con `/`:

```bash
curl -s -X POST http://localhost:9000/2015-03-31/functions/function/invocations --data-binary "@events/itinerary-created.json"
```

| Archivo | Primera vez | Segunda vez |
|---|---|---|
| `events\itinerary-created.json` | `PROCESSED`, `SENT` | `ALREADY_PROCESSED` |
| `events\itinerary-created-without-email.json` | `PROCESSED`, `SKIPPED` | `ALREADY_PROCESSED` |
| `events\invalid-event.json` | `REJECTED` con el motivo | `REJECTED` |

Con `docker stop notification-postgres`, cualquier invocación responde `"errorType": "TransientError"`.

Ver el historial:

```
docker exec notification-postgres psql -U notification -d notification_db -c "SELECT event_id, status, recipient, status_reason, correlation_id, processed_at FROM notification_history ORDER BY processed_at;"
```

## Variables de entorno

| Variable | Por defecto | Descripción |
|---|---|---|
| `DATABASE_URL` | — (obligatoria) | Desde el equipo: `...@localhost:5434/notification_db`. Dentro de Docker: `...@notification-postgres:5432/notification_db` |
| `DATABASE_CONNECT_TIMEOUT_SECONDS` | `3` | Espera máxima para conectar con PostgreSQL (mínimo 2); menor que el timeout de la función |
| `LOG_LEVEL` | `INFO` | Nivel de log del logger `app` |
| `AWS_LAMBDA_FUNCTION_TIMEOUT` | `10` (en el `Dockerfile`) | Timeout de la función en el emulador; en AWS se configura en la función |

## Pruebas

Con el entorno virtual activado (igual en PowerShell, CMD y zsh):

```
pytest -v
```

Resultado esperado: **60 passed** con `notification-postgres` y la migración aplicada; **54 passed, 6 skipped** sin
él. Las pruebas de integración **borran** las filas de `notification_history`.

## Posibles errores

| Síntoma | Causa | Solución |
|---|---|---|
| `ALREADY_PROCESSED` en la primera invocación, con la tabla vacía | El contenedor usa una imagen vieja | `docker build`, `docker rm -f send-notification-function` y `docker run` otra vez |
| `relation "notification_history" does not exist` | Falta la migración | `alembic upgrade head` |
| `Runtime.UnmarshalError` | El cuerpo enviado no es JSON | Usar los archivos de `events\` con `--data-binary "@..."` (en macOS, `"@events/..."`: con `\` curl no encuentra el archivo) |
| `port is already allocated` | Ya hay algo en el puerto 9000 o 5434 | `docker ps` y detener el otro contenedor |
| `could not translate host name "notification-postgres"` | La función no está en la red `notification-net` | Recrear el contenedor con `--network notification-net` |

## Estructura

```
app/
  domain/                → NotificationRecord, NotificationStatus, excepciones
  application/           → ItineraryCreatedEvent (vista del consumidor), puertos, caso de uso, excepciones
  infrastructure/
    notification/        → SimulatedEmailSender
    persistence/         → engine, modelo ORM, repositorio, unit of work, traducción a TransientError
  event_schema.py        → esquema Pydantic del contrato v1 (Tolerant Reader)
  handler.py             → handler(event, context): adaptador de entrada de Lambda
  config.py
alembic/                 → migración d1e5f7a3b9c2 (notification_history)
events/                  → eventos de ejemplo para curl.exe (curl en macOS)
tests/                   → dominio, caso de uso, esquema, handler, errores de BD e integración
Dockerfile               → imagen de Lambda (sin Alembic ni pruebas)
```
