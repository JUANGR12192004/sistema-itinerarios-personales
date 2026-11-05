# Itinerary Service

Microservicio de gestión de itinerarios de viaje. Permite crear, consultar, actualizar y eliminar itinerarios entre aeropuertos colombianos. Valida que los aeropuertos existan consultando Airport Service antes de guardar.

## Requisitos previos

- Python 3.12
- Docker Desktop (para PostgreSQL)
- Airport Service corriendo en `http://localhost:8001`
- RabbitMQ (Docker) para publicar eventos (Fase 4). Sin RabbitMQ el servicio funciona, pero los eventos se pierden

## Configuración inicial (una vez por equipo)

```powershell
# Permitir activar entornos virtuales
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

## Instalación

```powershell
cd services\itinerary-service
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Base de datos PostgreSQL

```powershell
# Levantar el contenedor (solo la primera vez o si no está corriendo)
docker run -d --name itinerary-postgres `
  -e POSTGRES_USER=itinerary `
  -e POSTGRES_PASSWORD=itinerary `
  -e POSTGRES_DB=itinerary_db `
  -p 5433:5432 `
  postgres:16-alpine

# Aplicar la migración
cd services\itinerary-service
.\.venv\Scripts\Activate.ps1
alembic upgrade head
```

## Variables de entorno

Copia `.env.example` a `.env` y ajusta los valores si es necesario:

```powershell
copy .env.example .env
```

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://itinerary:itinerary@localhost:5433/itinerary_db` | Conexión a PostgreSQL |
| `AIRPORT_SERVICE_URL` | `http://localhost:8001` | URL de Airport Service |
| `AIRPORT_SERVICE_TIMEOUT_SECONDS` | `5.0` | Timeout en segundos para llamadas a Airport Service |
| `RABBITMQ_URL` | `amqp://localhost:5672/%2F` (usuario `guest`) | Conexión a RabbitMQ |
| `RABBITMQ_TIMEOUT_SECONDS` | `3.0` | Timeout para conectar y publicar en RabbitMQ |
| `LOG_LEVEL` | `INFO` | Nivel de logging |

## RabbitMQ (Fase 4)

Itinerary Service publica `ItineraryCreatedEvent` en RabbitMQ cada vez que se crea un itinerario.
Hasta la Fase 10 (Docker Compose), RabbitMQ se ejecuta con un contenedor (igual en PowerShell y CMD):

```powershell
docker run -d --name itinerary-rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.13-management
```

- Puerto `5672`: protocolo AMQP (lo usa el servicio).
- Puerto `15672`: panel web en http://localhost:15672 (usuario y clave `guest`, solo para desarrollo local).
- No hace falta crear nada a mano: el servicio declara el exchange, las colas y los enlaces al publicar.

| Elemento | Nombre |
|---|---|
| Exchange | `itinerary.events` (topic, durable) |
| Routing key | `itinerary.created` |
| Cola | `notification.itinerary-created` (durable) |
| Dead letter exchange / cola | `itinerary.events.dlx` / `notification.itinerary-created.dlq` |

El contrato del evento está en [`docs/asyncapi/asyncapi.yaml`](../../docs/asyncapi/asyncapi.yaml)
y la explicación completa en [`docs/04-comunicacion-y-eventos.md`](../../docs/04-comunicacion-y-eventos.md).

## Ejecución

```powershell
cd services\itinerary-service
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

Swagger UI disponible en: `http://localhost:8002/docs`

## Pruebas

```powershell
cd services\itinerary-service
.\.venv\Scripts\Activate.ps1

# Todas las pruebas (las de integración se omiten si PostgreSQL o RabbitMQ no están disponibles)
pytest -v

# Solo pruebas unitarias y de API (sin PostgreSQL ni RabbitMQ)
pytest -v tests\domain tests\application tests\infrastructure tests\api

# Solo pruebas de integración (requiere PostgreSQL y RabbitMQ; la de RabbitMQ vacía la cola de notificaciones)
pytest -v tests\integration
```

## Endpoints

| Método | Ruta | Descripción | Éxito |
|---|---|---|---|
| `POST` | `/itineraries` | Crear itinerario | 201 |
| `GET` | `/itineraries` | Listar todos | 200 |
| `GET` | `/itineraries/{id}` | Obtener por ID | 200 |
| `PUT` | `/itineraries/{id}` | Actualizar | 200 |
| `DELETE` | `/itineraries/{id}` | Eliminar | 204 |
| `GET` | `/health` | Estado del servicio | 200 |

## Demostración de eventos (Fase 4)

Requisitos: PostgreSQL y RabbitMQ levantados, Airport Service en el puerto 8001 e Itinerary Service en el 8002.
Si la fecha `2026-12-15` ya pasó, cambiarla por una futura.

### 1. Crear un itinerario y ver el evento en la cola

**PowerShell:**

```powershell
$body = @{
  traveler_name        = "Ana Perez"
  traveler_email       = "ana@example.com"
  departure_airport_id = 1
  arrival_airport_id   = 5
  travel_date          = "2026-12-15T08:00:00-05:00"
  duration_minutes     = 75
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8002/itineraries `
  -ContentType "application/json" -Headers @{ "X-Correlation-ID" = "demo-fase-4" } -Body $body

# Leer el mensaje de la cola sin sacarlo (API del panel de RabbitMQ)
curl.exe -s -u guest:guest -H "Content-Type: application/json" `
  -X POST http://localhost:15672/api/queues/%2F/notification.itinerary-created/get `
  -d '{\"count\":1,\"ackmode\":\"ack_requeue_true\",\"encoding\":\"auto\"}'
```

**CMD:**

```cmd
chcp 65001
curl.exe -s -X POST http://localhost:8002/itineraries -H "Content-Type: application/json" -H "X-Correlation-ID: demo-fase-4" -d "{\"traveler_name\":\"Ana Perez\",\"traveler_email\":\"ana@example.com\",\"departure_airport_id\":1,\"arrival_airport_id\":5,\"travel_date\":\"2026-12-15T08:00:00-05:00\",\"duration_minutes\":75}"

curl.exe -s -u guest:guest -H "Content-Type: application/json" -X POST http://localhost:15672/api/queues/%2F/notification.itinerary-created/get -d "{\"count\":1,\"ackmode\":\"ack_requeue_true\",\"encoding\":\"auto\"}"
```

Resultado esperado:

- La API responde **201** con el itinerario.
- El log del servicio muestra `Evento publicado: itinerary.created event_id=... correlation_id=demo-fase-4`.
- La cola devuelve un mensaje cuyo `payload` es el evento (con `"event_type": "itinerary.created"` y el
  mismo `itinerary_id`) y cuyas propiedades traen `message_id` = `event_id` y `delivery_mode` = 2.
- También se ve en el panel: **Queues and Streams → notification.itinerary-created → Get messages**.

### 2. Demostrar el problema de double write

```powershell
docker stop itinerary-rabbitmq
```

Crear otro itinerario con el mismo comando del paso 1:

- La API responde **201**: el itinerario quedó guardado (aparece en `GET /itineraries`).
- El log muestra `ERROR ... Evento perdido: itinerario <id> guardado pero itinerary.created (event_id=...) no se publicó`.
- Al volver a levantar RabbitMQ (`docker start itinerary-rabbitmq`), ese evento **no está** en la cola.

El itinerario existe pero el sistema de notificaciones nunca se enterará: son dos escrituras
(PostgreSQL y RabbitMQ) sin una transacción común. La Fase 5 lo resuelve con el Transactional Outbox.

## Estructura

```
app/
  domain/           → Itinerary (agregado), reglas de negocio, excepciones
  application/      → Puertos (interfaces), casos de uso, excepciones de aplicación
  infrastructure/
    persistence/    → SqlAlchemyItineraryRepository, modelos ORM, session factory
    airport_client/ → HttpAirportCatalogAdapter (llama a Airport Service)
    messaging/      → RabbitMQEventPublisher y topología de RabbitMQ (Fase 4)
  api/              → Rutas, esquemas Pydantic, manejador de errores, dependencias
  main.py           → Creación de la app FastAPI
alembic/            → Migraciones de base de datos
tests/
  domain/           → Pruebas de dominio (sin dependencias externas)
  application/      → Pruebas de FakeItineraryRepository
  infrastructure/   → Pruebas de HttpAirportCatalogAdapter (respx)
  integration/      → Pruebas contra PostgreSQL real (SKIPPED en CI)
  api/              → Pruebas de rutas con fakes inyectados
```
