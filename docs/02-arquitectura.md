
# 02. Arquitectura del sistema

## 1. Estilo arquitectónico

El sistema combinará tres enfoques:

1. **Microservicios:** servicios independientes, con responsabilidades delimitadas.
2. **Arquitectura basada en eventos:** comunicación asíncrona para reaccionar a la creación de itinerarios.
3. **Serverless:** ejecución de SendNotificationFunction como una función activada por eventos.

La arquitectura hexagonal se aplicará dentro de los servicios que necesiten separar las reglas de negocio de los mecanismos externos.

DDD se utilizará como guía para definir los límites del dominio y establecer un lenguaje común.

## 2. Componentes principales

### 2.1. Airport Service

Responsabilidades:

- Consultar información de aeropuertos mediante API Colombia.
- Exponer endpoints REST.
- Definir un puerto de salida para consultar proveedores de aeropuertos.
- Implementar un Adapter para la API externa.
- Transformar respuestas externas al modelo interno.
- Permitir consultas por identificador.
- Preparar datos para la visualización en el mapa.
- Incorporar Redis, timeout, retry y circuit breaker en la fase de resiliencia.

Airport Service será propietario de la integración con API Colombia.

El dominio no dependerá directamente de las estructuras de respuesta de esa API.

### 2.2. Itinerary Service

Responsabilidades:

- Crear, consultar, actualizar y eliminar itinerarios.
- Aplicar las reglas de negocio del dominio de itinerarios.
- Validar aeropuertos mediante HTTP hacia Airport Service.
- Persistir itinerarios en su propia base de datos PostgreSQL.
- Gestionar sus migraciones mediante Alembic.
- Publicar el evento de integración de creación.
- Incorporar Transactional Outbox en la fase correspondiente.

### 2.3. Sistema de notificaciones

Formado por **Event Trigger + SendNotificationFunction + su base de datos** (Fase 6). No hay un microservicio de notificaciones adicional.

Responsabilidades:

- Recibir el evento de integración de creación de itinerarios.
- Procesar el evento de forma asíncrona.
- Activar SendNotificationFunction con cada evento.
- Simular el envío de una notificación.
- Registrar el historial de procesamiento.
- Gestionar fallos de procesamiento.

**Event Trigger** (`serverless/event-trigger`, ADR-031). Proceso que cumple el papel del *Event Source Mapping* de AWS Lambda:

- Consume la cola `notification.itinerary-created` con ACK manual y `prefetch_count=1`.
- Invoca la función por HTTP y decide según la respuesta: ACK, reintentar o enviar a la DLQ.
- Declara su cola, la DLX y la DLQ (ADR-032).
- Incluye el comando `python -m app.replay_dlq`, que devuelve a la cola los mensajes de la DLQ una vez corregida la causa del fallo.

**Persistencia:** PostgreSQL propio, `notification_db`, en el contenedor `notification-postgres` (ADR-029).

### 2.4. SendNotificationFunction

Función serverless (FaaS) en `serverless/send-notification-function` (ADR-008 y ADR-028). Se ejecuta con la imagen oficial de AWS Lambda para Python 3.12 y el Runtime Interface Emulator. Es responsable de:

- Recibir el evento como `handler(event, context)`.
- Validar su contenido contra el contrato v1 (si no lo cumple, responde `REJECTED`).
- Simular el envío de la notificación (`SimulatedEmailSender`).
- Registrar el resultado en `notification_history`, de forma **idempotente** con `event_id` (ADR-030).
- Manejar errores: si su base de datos no está disponible, lanza `TransientError` para que el trigger reintente.

No guarda estado entre invocaciones y no conoce RabbitMQ. La función no es responsable de administrar itinerarios ni de implementar sus reglas de negocio.

### 2.5. API Gateway

Nginx en Docker (Fase 7, ADR-009), en el puerto 8000. Es el punto único de entrada para el frontend y cualquier otro cliente.

Responsabilidades:

- Enrutar `/api/airports/...` a Airport Service y `/api/itineraries/...` a Itinerary Service, quitando el prefijo `/api`.
- Aplicar rate limiting por IP de origen (10 solicitudes por segundo, ráfaga de 20; 429 al superarlo).
- Reenviar el header `Authorization` sin validarlo (preparación de JWT).
- Reenviar o generar `X-Correlation-ID`, para que la trazabilidad empiece en el gateway.
- Aplicar timeouts hacia los servicios y responder sus propios errores (502, 504, 404, 413, 429) en el formato único de errores.
- Más adelante, servir el frontend desde el mismo origen (Fase 8).

**No tiene lógica de negocio.** Las reglas viven en el dominio de cada servicio. Si se copiaran en el gateway, habría dos fuentes de verdad, y un componente que comparten todos tendría que cambiar con cada regla nueva. Por eso es un **API Gateway** genérico y no un **BFF** (*Backend for Frontend*), que sí juntaría y transformaría respuestas para una pantalla concreta.

La comunicación entre servicios (Itinerary → Airport) no pasa por el gateway.

### 2.6. Frontend

Responsabilidades:

- Consultar los servicios internos.
- Mostrar aeropuertos mediante Plotly JS.
- Permitir la gestión de itinerarios.
- Presentar errores y resultados al usuario.

No consumirá directamente la API externa.

## 3. Comunicación entre componentes

### Comunicación síncrona

Se utilizará HTTP/REST cuando un componente necesite una respuesta inmediata.

Desde afuera (tráfico *norte-sur*):

Cliente / Frontend → API Gateway (:8000) → Airport Service o Itinerary Service

Entre servicios (tráfico *este-oeste*, sin pasar por el gateway):

Itinerary Service → Airport Service

El servicio de itinerarios consulta la existencia de los aeropuertos antes de guardar el itinerario.

### Comunicación asíncrona

Se utilizará RabbitMQ para transportar eventos de integración.

Ejemplo:

Itinerary Service → outbox → Outbox Relay → RabbitMQ → Event Trigger → SendNotificationFunction

El emisor no espera a que termine la simulación de la notificación: responde 201 en cuanto el itinerario y su evento quedan guardados en la misma transacción.

Confiabilidad de la entrega:

- Transactional Outbox y Outbox Relay (Fase 5): el evento no se pierde aunque RabbitMQ esté caído.
- Entrega "al menos una vez" con consumidor idempotente (Fase 6).
- Reintentos y DLQ en el Event Trigger (ADR-031).

El detalle está en `04-comunicacion-y-eventos.md`.

## 4. Persistencia y propiedad de datos

### Base de datos de itinerarios

Itinerary Service será propietario de los itinerarios almacenados en su PostgreSQL.

### Base de datos o almacenamiento de notificaciones

El historial de notificaciones tiene persistencia propia, separada de los datos de itinerarios: PostgreSQL `notification_db` en el contenedor `notification-postgres` (puerto 5434), tabla `notification_history` (ADR-029). Sus migraciones se aplican aparte con Alembic, no en cada invocación de la función.

### Aeropuertos

La fuente externa de información será API Colombia. La incorporación de Redis permitirá almacenar temporalmente resultados de consultas.

No se ha definido todavía una base de datos persistente propia para Airport Service.

## 5. Resiliencia

Airport Service incorporará progresivamente:

- Timeout: limita cuánto puede esperar una solicitud.
- Retry: permite repetir operaciones fallidas de forma controlada.
- Exponential Backoff: incrementa el intervalo entre reintentos.
- Circuit Breaker: evita insistir continuamente contra una dependencia que falla.
- Redis: reduce consultas repetidas a la API externa.
- Fallback: permite una respuesta alternativa cuando sea válida y segura.

Los reintentos se limitarán a operaciones apropiadas y no deben multiplicar innecesariamente la carga sobre el proveedor externo.

## 6. Observabilidad

La solución incorpora tres capas de observabilidad (Fase 9) que permiten seguir una operación desde el frontend hasta los servicios, la base de datos y el procesamiento del evento.

### 6.1. Logs estructurados en JSON (ADR-034)

Los cuatro componentes Python producen logs en formato JSON con `python-json-logger`. Cada línea incluye los campos `timestamp`, `level`, `service`, `logger`, `message`, `correlation_id`, `trace_id` y `span_id`.

Dos filtros inyectan los valores dinámicos en cada línea:

- **`CorrelationIdFilter`:** lee el `correlation_id` de una `ContextVar` que se establece al principio de cada solicitud HTTP (desde el header `X-Correlation-ID`).
- **`OTelContextFilter`:** lee el `trace_id` y el `span_id` del span activo de OpenTelemetry. Si no hay span activo (por ejemplo, en el Outbox Relay fuera de un ciclo de procesamiento), los campos quedan vacíos.

La función `configure_logging(log_level, service_name)` en `app/logging_config.py` configura el logger raíz `app` y es idempotente. El nivel de log se controla con la variable `LOG_LEVEL` (por defecto `INFO`).

### 6.2. Trazas distribuidas (ADR-035, ADR-036, ADR-037, ADR-039)

La instrumentación usa **OpenTelemetry SDK 1.45.2** con exportador OTLP gRPC hacia **Jaeger 2.23.0** (puerto 4317 OTLP, puerto 16686 interfaz de usuario). La variable `OTEL_ENABLED=false` desactiva el envío de trazas sin cambiar el código.

Cada componente instrumenta sus propias dependencias:

| Componente | Librerías instrumentadas |
|---|---|
| Airport Service | FastAPI, httpx, Logging |
| Itinerary Service | FastAPI, httpx, SQLAlchemy, pika, Logging |
| Outbox Relay | pika, Logging |
| Event Trigger | pika, Logging |
| SendNotificationFunction | SQLAlchemy, Logging |
| API Gateway | `ngx_otel_module` (imagen `nginx:1.30.6-alpine-otel`, ADR-036) |

La propagación del contexto W3C (header `traceparent`) conecta los spans de distintos componentes en una sola traza. El API Gateway inyecta `traceparent` en las solicitudes hacia los servicios (`otel_trace_context propagate`). El Itinerary Service lo captura al registrar el evento en la outbox, guardándolo en la columna `traceparent` de `outbox_events` (migración `e6f0a4b8c1d9`, ADR-037); el Outbox Relay lo restaura antes de publicar en RabbitMQ, y el Event Trigger lo extrae de los headers AMQP para pasarlo a la función.

En las pruebas se usa `InMemorySpanExporter` con `SimpleSpanProcessor`: no es necesario tener Jaeger corriendo.

### 6.3. Métricas (ADR-038)

Los cuatro componentes exponen métricas en formato Prometheus (`prometheus-client==0.21.1`):

| Componente | Puerto | Endpoint | Métricas |
|---|---|---|---|
| Airport Service | 8001 | `/metrics` | `http_requests_total`, `http_request_duration_seconds` |
| Itinerary Service | 8002 | `/metrics` | `http_requests_total`, `http_request_duration_seconds`, `itineraries_created_total` |
| Outbox Relay | 9101 | `/` | `outbox_events_published_total`, `outbox_events_failed_total`, `outbox_events_dead_total`, `outbox_relay_cycles_total` |
| Event Trigger | 9102 | `/` | `notifications_dispatched_total{outcome}` |

**Prometheus** (puerto 9090) consulta los cuatro endpoints cada 15 segundos. **Grafana** (puerto 3000) muestra un dashboard preconfigurado con cuatro paneles: negocio (itinerarios creados, notificaciones, relay), solicitudes HTTP por servicio (rate y distribución), latencia (p50/p95/p99 por servicio) y detalle del relay y el trigger. El datasource y el dashboard se cargan al arrancar Grafana desde `observability/grafana/provisioning/`.

## 7. Despliegue

Docker y Docker Compose facilitarán el entorno de desarrollo local.

La orquestación completa se construirá en su fase específica, cuando los componentes ya se hayan implementado y probado individualmente.

## 8. Principios de diseño

- Separación de responsabilidades.
- Bajo acoplamiento.
- Alta cohesión.
- Propiedad de datos por servicio.
- Contratos explícitos entre componentes.
- Adaptación de dependencias externas mediante puertos y adaptadores.
- Procesamiento asíncrono para operaciones desacopladas.
- Complejidad proporcional a las necesidades del proyecto.
