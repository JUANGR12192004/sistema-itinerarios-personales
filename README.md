
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
2. **Itinerary Service:** creación, consulta, actualización y eliminación de itinerarios.
3. **Sistema de notificaciones:** procesamiento de eventos y registro del historial.
4. **SendNotificationFunction:** función serverless para procesar notificaciones.
5. **API Gateway / BFF:** punto de entrada para las solicitudes del frontend.
6. **Frontend:** interfaz de gestión de itinerarios y visualización de aeropuertos.

La implementación se desarrollará progresivamente, siguiendo las fases definidas en la documentación del proyecto.

## Tecnologías previstas

| Área | Tecnología |
|---|---|
| Backend | Python, FastAPI, Pydantic |
| Persistencia | PostgreSQL |
| ORM y migraciones | SQLAlchemy y Alembic |
| Comunicación síncrona | HTTP / REST |
| Mensajería | RabbitMQ |
| Caché | Redis |
| Frontend | HTML, CSS, JavaScript |
| Visualización | Plotly JS |
| Contenedores | Docker y Docker Compose |
| Serverless local | Alternativa por definir en la planificación técnica |
| Observabilidad | OpenTelemetry, Jaeger, Prometheus y Grafana |
| Documentación API | Swagger / OpenAPI y AsyncAPI |
| Pruebas | Frameworks de pruebas de Python y pruebas de integración |

## Arquitectura

El sistema utilizará microservicios con responsabilidades delimitadas, comunicación HTTP para las operaciones que necesitan una respuesta inmediata y mensajería asíncrona para los eventos de integración.

Cada microservicio de negocio tendrá su propia base de datos lógica y será responsable de sus propios datos.

Se aplicarán arquitectura hexagonal, el patrón Adapter y conceptos de DDD para mantener separadas las reglas de negocio y los detalles de infraestructura.

## Estructura documental

- `docs/01-planificacion.md`: objetivos, alcance, requisitos y fases.
- `docs/02-arquitectura.md`: arquitectura general y responsabilidades.
- `docs/03-dominio.md`: dominio, contextos delimitados y lenguaje ubicuo.
- `docs/04-comunicacion-y-eventos.md`: comunicación HTTP y eventos.
- `docs/05-diagramas.md`: diagramas arquitectónicos en Mermaid.
- `docs/06-decisiones-arquitectonicas.md`: registro de decisiones técnicas.

## Estado del proyecto

| Fase | Nombre | Estado |
|---|---|---|
| 0 | Planificación y arquitectura | Completada |
| 1 | Airport Service | Completada |
| 2 | Resiliencia y caché | Completada |
| 3 | Itinerary Service | Completada |
| 4 | Eventos y RabbitMQ | Completada |
| 5 | Transactional Outbox | En revisión (rama `fase-5-transactional-outbox`) |
| 6 a 12 | Serverless, gateway, frontend, observabilidad, Docker, pruebas y documentación | Pendientes |

**Fase actual:** Fase 5 — Transactional Outbox. Implementada en la rama `fase-5-transactional-outbox`, pendiente de pull request y merge.

La documentación de Itinerary Service (PostgreSQL, Alembic, RabbitMQ, Outbox Relay, ejecución, pruebas, endpoints y demostración) está en [`services/itinerary-service/README.md`](services/itinerary-service/README.md). El contrato del evento `ItineraryCreatedEvent` está en [`docs/asyncapi/asyncapi.yaml`](docs/asyncapi/asyncapi.yaml).

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

### Fase 2 — Resiliencia y caché (completada)

Airport Service tolera los fallos de API Colombia sin cambiar sus casos de uso ni el Adapter: la caché y la resiliencia se agregan como Decorators del puerto `AirportProvider`.

| Mecanismo | Comportamiento |
|---|---|
| Caché en Redis | Respuestas guardadas 10 minutos; header `X-Cache: HIT` o `MISS` |
| Timeout | 3 s por llamada; si se agota en todos los intentos → 504 `AIRPORT_PROVIDER_TIMEOUT` |
| Retry con exponential backoff | 3 intentos con esperas de 0.5 s y 1 s; no se reintentan 404 ni 502 |
| Circuit breaker | Tras 3 consultas fallidas seguidas responde 503 al instante durante 30 s |
| Fallback | Si API Colombia no está disponible, responde la copia de respaldo (24 h) con `X-Cache: STALE` |

Orden: caché → circuit breaker → retry con backoff → llamada con timeout → fallback. Si Redis no está disponible, el servicio sigue funcionando sin caché. Decisiones en ADR-007 y ADR-014 (`docs/06-decisiones-arquitectonicas.md`).

La documentación de Airport Service (instalación, Redis, ejecución, pruebas, endpoints y demostración de los escenarios de resiliencia) está en [`services/airport-service/README.md`](services/airport-service/README.md).

## Desarrollo

El desarrollo seguirá un enfoque incremental. Cada fase incluirá explicación, estructura de archivos, implementación cuando corresponda, instrucciones de ejecución, pruebas y una lista de verificación.

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

- Cada rama `fase-N-...` se **conserva después del merge como archivo de solo lectura**: muestra los commits de cada entrega de esa fase. No se trabaja en ellas después de fusionarlas; cualquier corrección sale de una rama nueva desde `main`.
- Las ramas auxiliares (`chore/`, `fix/`, `docs/`) se borran después del merge.
- Cada etiqueta `fase-N` apunta al commit del merge de esa fase en `main`. Para ver el sistema tal como quedó al cerrar una fase: `git switch --detach fase-3`.

## Uso de Claude Code

El equipo usa [Claude Code](https://claude.com/claude-code) como herramienta de desarrollo (asistente de programación). Las reglas que sigue en este repositorio están en [`CLAUDE.md`](CLAUDE.md), y cada cambio que propone lo revisa, confirma y sube un integrante del equipo, que es el autor del commit.

Los commits y las descripciones de pull request **no llevan la línea de coautoría** de Claude (`Co-Authored-By`); está desactivada en `.claude/settings.json`. Los commits de la Fase 3 sí la conservan porque son anteriores a esta regla, y el equipo decidió no volver a reescribir el historial de `main`.

## Contexto académico

Proyecto universitario para la asignatura Arquitecturas de Software Emergentes.
