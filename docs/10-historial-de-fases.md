
# 10. Historial de fases

> Estos resúmenes estaban en el `README.md` raíz (uno por fase, del más reciente al más antiguo) y se movieron aquí en
> la Fase 12, ordenados de la Fase 2 a la 11. Los conceptos que explican están resumidos en la sección
> [Arquitectura](../README.md#arquitectura) del README raíz.

Dónde está el resto de la historia del proyecto:

- **Estado detallado de cada fase y entrega** (commits, pruebas, demostraciones, hallazgos): sección 15 de
  [`CLAUDE.md`](../CLAUDE.md).
- **Código de cada fase tal como quedó al cerrarla**: etiquetas `fase-1` a `fase-12` y ramas `fase-N-...` (tabla de
  ramas en [Desarrollo por fases](../README.md#desarrollo-por-fases-ramas-y-etiquetas) del README raíz).
- **Por qué se tomó cada decisión**: [`06-decisiones-arquitectonicas.md`](06-decisiones-arquitectonicas.md).
- **Planificación original (Fase 0)**: [`01-planificacion.md`](01-planificacion.md).

## Fase 2 — Resiliencia y caché

Airport Service tolera los fallos de API Colombia sin cambiar sus casos de uso ni el Adapter: la caché y la resiliencia se agregan como Decorators del puerto `AirportProvider`.

| Mecanismo | Comportamiento |
|---|---|
| Caché en Redis | Respuestas guardadas 10 minutos; header `X-Cache: HIT` o `MISS` |
| Timeout | 3 s por llamada; si se agota en todos los intentos → 504 `AIRPORT_PROVIDER_TIMEOUT` |
| Retry con exponential backoff | 3 intentos con esperas de 0.5 s y 1 s; no se reintentan 404 ni 502 |
| Circuit breaker | Tras 3 consultas fallidas seguidas responde 503 al instante durante 30 s |
| Fallback | Si API Colombia no está disponible, responde la copia de respaldo (24 h) con `X-Cache: STALE` |

Orden: caché → circuit breaker → retry con backoff → llamada con timeout → fallback. Si Redis no está disponible, el servicio sigue funcionando sin caché. Decisiones en ADR-007 y ADR-014 (`docs/06-decisiones-arquitectonicas.md`).

## Fase 5 — Transactional Outbox

Resuelve el problema de *double write* de la Fase 4 (guardar en PostgreSQL y publicar en RabbitMQ sin una transacción común), sin cambiar el contrato del evento.

| Pieza | Qué hace |
|---|---|
| Tabla `outbox_events` | Guarda el evento en la **misma transacción** que el itinerario: se guardan los dos o ninguno (ADR-024, ADR-026) |
| Outbox Relay (`python -m app.outbox_relay`) | Proceso aparte que publica los pendientes con `FOR UPDATE SKIP LOCKED` y los marca como publicados (ADR-025) |
| Fallo temporal (RabbitMQ caído) | El evento sigue pendiente y se reintenta sin límite: no se pierde |
| Fallo permanente (mensaje ilegible) | Se descarta con `failed_at` para que no bloquee a los demás (ADR-027) |
| Entrega al menos una vez | Puede haber duplicados: el consumidor debe ser idempotente con `event_id` |

La explicación completa está en [`docs/04-comunicacion-y-eventos.md`](04-comunicacion-y-eventos.md) (sección 7).

## Fase 6 — Serverless

| Pieza | Qué hace |
|---|---|
| SendNotificationFunction | Función FaaS `handler(event, context)` en una imagen de AWS Lambda con el RIE (puerto 9000). Simula el correo y guarda el historial en `notification_db`, de forma idempotente con `event_id` (ADR-008, ADR-028 a ADR-030) |
| Event Trigger (`python -m app.main`) | Equivalente al Event Source Mapping de AWS: consume la cola, invoca la función y confirma, reintenta o envía a la DLQ (ADR-031) |
| Fallo de infraestructura | Función o su base de datos caídas: se reintenta sin límite y nunca va a la DLQ |
| Fallo permanente o error de la función | Evento inválido: a la DLQ sin reintentos. Error de la función: 3 intentos y después a la DLQ |
| Reprocesamiento (`python -m app.replay_dlq`) | Devuelve a la cola los mensajes de la DLQ una vez corregido el problema |
| Propiedad de la topología | Itinerary Service declara solo su exchange; el trigger declara su cola, la DLX y la DLQ. Si el trigger no ha arrancado, el evento espera en la outbox (ADR-032) |

La explicación completa (qué es FaaS y por qué esta función lo es aunque corra en Docker) está en
[`docs/04-comunicacion-y-eventos.md`](04-comunicacion-y-eventos.md), sección 8.

## Fase 7 — API Gateway

Punto único de entrada en `http://localhost:8000`: **Nginx** en Docker, sin lógica de negocio (ADR-009). Toda la
documentación está en [`gateway/README.md`](../gateway/README.md).

| Pieza | Qué hace |
|---|---|
| Enrutamiento | `/api/airports/...` → Airport Service y `/api/itineraries/...` → Itinerary Service, sin el prefijo `/api`. La llamada Itinerary → Airport es interna y no pasa por el gateway |
| Rate limiting | 10 solicitudes por segundo por IP, con ráfaga de 20, solo en `/api/`. Al superarlo: 429 `RATE_LIMIT_EXCEEDED` |
| `X-Correlation-ID` | Se reenvía si es válido; si no, el gateway genera uno. Viaja al evento y al historial de notificaciones |
| `Authorization` | Se reenvía sin validarlo (preparación de JWT) |
| Errores propios | 502 `UPSTREAM_UNAVAILABLE`, 504 `UPSTREAM_TIMEOUT`, 404 `ROUTE_NOT_FOUND`, 413 `PAYLOAD_TOO_LARGE` en el formato único. Los errores de los servicios pasan sin cambios |
| Pruebas | Contenedores propios del gateway contra servidores eco: no tocan datos reales ni el límite del gateway de la demostración |

## Fase 8 — Frontend

Interfaz web servida por el mismo contenedor del API Gateway. Mapa de aeropuertos con Plotly JS y CRUD de itinerarios (ADR-033).

| Pieza | Qué hace |
|---|---|
| Mapa de aeropuertos | `scattergeo` de Plotly 4.3.0 (bundle parcial local), centrado en Colombia, un color por tipo, tooltip con nombre, IATA, ciudad y departamento |
| CRUD de itinerarios | Formulario de 2 columnas con desplegables de aeropuertos; tabla con edición inline y eliminación con confirmación |
| `datetime-local` → ISO 8601 | La fecha se envía con el offset del navegador (ADR-017) |
| Errores del gateway | Se muestran con `correlation_id` y botón "Copiar" en 5xx |
| Sin `innerHTML` | Todo texto de datos con `textContent` para evitar XSS |

## Fase 9 — Observabilidad

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
| Prometheus (puerto 9090) | Consulta los cuatro endpoints cada 15 s. Configurado en `observability/prometheus/prometheus.yml` en el modo manual y en `prometheus.compose.yml` con Docker Compose (Fase 10) |
| Grafana (puerto 3000) | Dashboard preconfigurado con paneles de negocio, HTTP, latencia (p50/p95/p99) y relay/trigger. Provisioning automático desde `observability/grafana/provisioning/` |

La demostración completa está en la sección [Demostración de observabilidad](08-demostraciones.md#demostración-de-observabilidad).

## Fase 10 — Docker y Docker Compose

Todo el sistema se levanta con **un solo comando**: `docker compose up -d --build` (ADR-041). Solo hace falta Docker
Desktop; Python 3.12 sigue haciendo falta para desarrollar y ejecutar las pruebas. Ver
[Instalación y ejecución](../README.md#instalación-y-ejecución).

| Pieza | Qué hace |
|---|---|
| Imágenes propias | Airport Service, Itinerary Service (una imagen para la API, el relay y las migraciones), Event Trigger y migraciones de notificaciones, sobre `python:3.12-slim` con usuario sin privilegios |
| Migraciones automáticas | `itinerary-migrations` y `notification-migrations` aplican `alembic upgrade head` y terminan; la API, el relay y la función esperan a que terminen con éxito |
| Orden de arranque con healthchecks | `depends_on` espera a que PostgreSQL y RabbitMQ estén listos: ya no hay que seguir el orden a mano |
| Redes por base de datos | Cada PostgreSQL solo es visible para los contenedores de su servicio dueño |
| Mismos puertos de siempre | Gateway 8000, servicios 8001/8002, bases 5433/5434, RabbitMQ 5672/15672, Jaeger 16686, Prometheus 9090, Grafana 3000 |
| Observabilidad incluida | Jaeger, Prometheus (`prometheus.compose.yml`) y Grafana con el dashboard cargado al arrancar |
| CI | Job "Docker Compose": valida el archivo, construye las imágenes, levanta el sistema y comprueba los healthchecks y el gateway |

## Fase 11 — Pruebas

Pirámide de pruebas en cinco niveles (ADR-042; cómo correr cada uno en [Pruebas](../README.md#pruebas)):

- **Bases propias de las pruebas de integración**: `itinerary_db_test` y `notification_db_test`, creadas y migradas
  por las propias pruebas. Ya no borran datos de las bases reales.
- **Pruebas de `libs/observability`** con su job de CI.
- **Pruebas de contrato**: Airport Service publica su API en `docs/openapi/airport-service.json` e Itinerary Service
  la verifica como consumidor; SendNotificationFunction verifica el evento contra AsyncAPI.
- **Pruebas de punta a punta** (`tests/e2e`) sobre Docker Compose con un simulador de API Colombia
  (`docker-compose.e2e.yml`): CRUD, outbox → RabbitMQ → función → historial, una traza en Jaeger con los seis
  componentes y métricas en Prometheus. Las ejecuta el job "Docker Compose" del CI.
- **Salida limpia**: las advertencias de Starlette y pika (de terceros) se filtran con precisión.

Con todo encendido: **639 pruebas, 0 fallos, 0 omitidas** al cerrar la Fase 11. Después, la rama `fix/limpieza-config`
borró 21 pruebas que repetían las de `libs/observability` y movió una a ese paquete (619), en la Fase 12 se agregó una
prueba al Event Trigger (620) y las correcciones posteriores a la Fase 12 agregaron 22 más: el total vigente es
**642** (ver [Pruebas](../README.md#pruebas)).

## Correcciones posteriores a la Fase 12

Después del merge de la Fase 12 (PR #30, etiqueta `fase-12`) entraron dos correcciones de código. Cada una salió de una
rama nueva desde `main`, con sus pruebas, y está registrada como nota en el ADR correspondiente.

| Rama (PR) | Problema | Corrección |
|---|---|---|
| `fix/commit-antes-de-responder` (#32) | `PUT` y `DELETE /itineraries/{id}` **respondían antes de confirmar la transacción**: el commit estaba después del `yield` de la dependencia `get_db_session`, y FastAPI ejecuta ese código después de enviar la respuesta. Un `GET` inmediato podía ver todavía el itinerario borrado; lo detectó la prueba E2E `test_crud_completo_por_el_gateway`, que fallaba de forma intermitente en el CI | `UpdateItineraryUseCase` y `DeleteItineraryUseCase` confirman con `UnitOfWork` antes de devolver el resultado, como ya hacía la creación; la dependencia ya no hace commit. 10 pruebas nuevas en Itinerary Service (nota en ADR-019) |
| `fix/sonarcloud-fiabilidad` (#33) | SonarCloud marcaba la **fiabilidad en C** (9 problemas en Airport Service): la conexión con Redis no se cerraba si el `lifespan` terminaba con error, y los manejadores de errores eran `async` sin ningún `await`. Además, el log `ERROR` de un 500 salía **sin `correlation_id`** en Airport e Itinerary Service, aunque la respuesta sí lo llevaba | Cierre de Redis en un `finally`, manejadores como funciones normales y el `correlation_id` del 500 tomado de `request.state`. Fiabilidad de **C a A** (evidencia [19](evidencias/19-sonarcloud.png)). 8 pruebas nuevas en Airport y 4 en Itinerary |

Además, el equipo agregó las evidencias 19 (SonarCloud) y 20 (GitHub Actions) con los PR #31, #34 y #35.

## Mejora del frontend

Rama `feat/mejora-frontend` (2026-11-23), en tres entregas. Sigue siendo HTML, CSS y JavaScript sin framework, sin
build y sin CDN, y solo habla con el gateway (nota en ADR-033).

| Entrega | Qué cambió |
|---|---|
| Diseño visual | Paleta de «carta aeronáutica» en variables CSS, tema claro y oscuro con botón en la cabecera, fuente D-DIN local (SIL OFL 1.1), tarjetas, botones con estados, pie de página con el curso y el equipo, diseño para 375, 768 y 1280 px |
| Experiencia de uso | Barra de carga, avisos que se cierran solos, confirmación con `<dialog>`, validación antes de enviar (reglas de ADR-015), llegada estimada (salida + duración), buscador de aeropuertos, ruta de un itinerario resaltada en el mapa y estado vacío |
| Cierre | Pestañas con flechas, Inicio y Fin, enlace «Saltar al contenido», contraste AA comprobado en los dos temas, 7 pruebas nuevas en `test_static.py` (gateway: 60) y evidencias 10 a 14 regeneradas, más la 21 en modo oscuro |

Error real corregido en la segunda entrega: al editar un itinerario, el formulario mostraba la hora UTC que devuelve la
API como si fuera local; al guardar sin tocar la fecha, el viaje se corría 5 horas (en Colombia). Venía de la Fase 8.
