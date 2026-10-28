
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
| 3 | Itinerary Service | Siguiente |
| 4 a 12 | Eventos, Outbox, serverless, gateway, frontend, observabilidad, Docker, pruebas y documentación | Pendientes |

**Fase actual:** Fase 3 — Itinerary Service (CRUD de itinerarios con PostgreSQL y validación de aeropuertos contra Airport Service).

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

## Contexto académico

Proyecto universitario para la asignatura Arquitecturas de Software Emergentes.
