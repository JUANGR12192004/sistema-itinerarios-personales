
# 05. Diagramas arquitectónicos

## 1. Arquitectura general

```mermaid
flowchart TB
    U[Usuario] --> FE[Frontend]
    FE --> GW["API Gateway (Nginx) :8000"]

    GW -->|/api/airports| AS[Airport Service]
    GW -->|/api/itineraries| IS[Itinerary Service]

    IS -->|HTTP: validar aeropuertos| AS
    AS --> AD[API Colombia Adapter]
    AD --> EXT[API Colombia]

    AS -.-> REDIS[(Redis)]

    IS --> DBI[(PostgreSQL de itinerarios<br/>itineraries + outbox_events)]
    DBI --> PUB[Outbox Relay]
    PUB --> RMQ[RabbitMQ]

    subgraph NS["Sistema de notificaciones (Fase 6)"]
        TR[Event Trigger]
        FN["SendNotificationFunction<br/>(AWS Lambda + RIE)"]
        NH[("PostgreSQL de notificaciones<br/>notification_history")]
        TR -->|"HTTP: API Invoke de Lambda"| FN
        FN --> NH
    end
    RMQ --> TR

    FE --> MAP[Plotly JS]
```

El diagrama representa la arquitectura objetivo. Los componentes se incorporan progresivamente: el gateway llegó en la Fase 7 (Nginx, ADR-009) y el frontend llega en la Fase 8. La llamada Itinerary → Airport es interna y no pasa por el gateway.

El sistema de notificaciones está formado por el Event Trigger, la función y su base de datos `notification_db` (ADR-029). No hay un microservicio de notificaciones adicional.

## 2. Diagrama de componentes

```mermaid
flowchart LR
    CLI["Cliente / Frontend"] -->|"HTTP :8000"| GWN

    subgraph Gateway["API Gateway (Nginx, sin lógica de negocio)"]
        GWN["rate limiting · X-Correlation-ID<br/>reenvío de Authorization · timeouts"]
    end

    GWN -->|"/api/airports/... → /airports/..."| AC
    GWN -->|"/api/itineraries/... → /itineraries/..."| IC

    subgraph Airport["Airport Service"]
        AC[REST Controller]
        APP[Application Layer]
        PORT[Airport Provider Port]
        ADAPTER[API Colombia Adapter]
        CLIENT[HTTP Client]

        AC --> APP
        APP --> PORT
        ADAPTER -.->|implements| PORT
        ADAPTER --> CLIENT
    end

    EXT[API Colombia] <--> CLIENT

    subgraph Itinerary["Itinerary Service"]
        IC[REST Controller]
        UC[Use Cases]
        DOMAIN[Itinerary Domain]
        REPO[ItineraryRepository Port]
        PERSIST[PostgreSQL Adapter]
        CATALOG[AirportCatalog Port]
        HTTPADAPTER[HttpAirportCatalogAdapter]
        PUBPORT[EventPublisher Port]
        OUTBOXADAPTER[OutboxEventPublisher]

        IC --> UC
        UC --> DOMAIN
        UC --> REPO
        UC --> CATALOG
        UC --> PUBPORT
        PERSIST -.->|implements| REPO
        HTTPADAPTER -.->|implements| CATALOG
        OUTBOXADAPTER -.->|implements| PUBPORT
    end

    subgraph Relay["Outbox Relay (proceso aparte)"]
        RELAY[OutboxRelay]
        OUTPORT[OutboxRepository Port]
        OUTREPO[SqlAlchemyOutboxRepository]
        PUBPORT2[EventPublisher Port]
        MSGADAPTER[RabbitMQEventPublisher]

        RELAY --> OUTPORT
        RELAY --> PUBPORT2
        OUTREPO -.->|implements| OUTPORT
        MSGADAPTER -.->|implements| PUBPORT2
    end

    DB[(PostgreSQL<br/>itineraries + outbox_events)] <--> PERSIST
    OUTBOXADAPTER -->|INSERT en la misma transacción| DB
    OUTREPO <-->|"SELECT ... FOR UPDATE SKIP LOCKED"| DB
    HTTPADAPTER -->|"HTTP GET /airports/{id}"| AC
    MSGADAPTER -->|"publica en el exchange itinerary.events"| MQ[RabbitMQ]

    subgraph Trigger["Event Trigger (proceso aparte)"]
        CONSUMER[RabbitMQConsumer]
        POLICY[DeliveryHandler<br/>política de reintentos]
        INVPORT[FunctionInvoker Port]
        INVOKER[LambdaFunctionInvoker]

        CONSUMER --> POLICY
        POLICY --> INVPORT
        INVOKER -.->|implements| INVPORT
    end

    subgraph Function["SendNotificationFunction (FaaS)"]
        HANDLER["handler(event, context)"]
        NUC[NotifyItineraryCreatedUseCase]
        NDOMAIN[NotificationRecord]
        HISTPORT[NotificationHistoryRepository Port]
        SENDPORT[NotificationSender Port]
        HISTREPO[SqlAlchemyNotificationHistoryRepository]
        SENDER[SimulatedEmailSender]

        HANDLER --> NUC
        NUC --> NDOMAIN
        NUC --> HISTPORT
        NUC --> SENDPORT
        HISTREPO -.->|implements| HISTPORT
        SENDER -.->|implements| SENDPORT
    end

    MQ -->|"cola notification.itinerary-created"| CONSUMER
    INVOKER -->|"POST /2015-03-31/functions/function/invocations"| HANDLER
    HISTREPO <--> NDB[(PostgreSQL<br/>notification_history)]
```

Las flechas punteadas representan una relación de implementación conceptual de los puertos, no una llamada en tiempo de ejecución.

El API Gateway (Fase 7) solo enruta hacia los controladores REST de cada servicio; no conoce sus capas internas ni tiene lógica de negocio (ADR-009). Itinerary Service no accede a las capas internas de Airport Service: el adaptador `HttpAirportCatalogAdapter` llama a su API REST. Los casos de uso tampoco hablan directamente con RabbitMQ: usan el puerto `EventPublisher`, implementado en la Fase 4 por un publicador de RabbitMQ y en la Fase 5 por un adaptador Outbox, que registra el evento antes del commit, en la misma transacción del itinerario (ADR-013, ADR-026).

El mismo puerto `EventPublisher` tiene dos adaptadores, uno en cada proceso: en la API, `OutboxEventPublisher` guarda el evento en `outbox_events`; en el Outbox Relay, `RabbitMQEventPublisher` (el de la Fase 4, sin cambios) lo publica en RabbitMQ. El relay lee y marca los pendientes con su propio puerto, `OutboxRepository` (ADR-025).

En el sistema de notificaciones (Fase 6), el Event Trigger separa la **política** (`DeliveryHandler`, capa de aplicación) de los adaptadores: el consumidor de RabbitMQ y el cliente HTTP de la función (ADR-031). La función sigue la arquitectura hexagonal por dentro: el handler de Lambda es el adaptador de entrada, como una ruta FastAPI (ADR-028).

## 3. Secuencia de creación de un itinerario

```mermaid
sequenceDiagram
    actor Usuario
    participant FE as Frontend
    participant GW as API Gateway
    participant IS as Itinerary Service
    participant AS as Airport Service
    participant DB as PostgreSQL
    participant R as Outbox Relay
    participant MQ as RabbitMQ
    participant TR as Event Trigger
    participant NF as SendNotificationFunction
    participant NH as PostgreSQL notificaciones

    Usuario->>FE: Crear itinerario
    FE->>GW: POST /api/itineraries
    Note over GW: Rate limiting (429 si se supera)<br/>X-Correlation-ID: se reenvía o se genera
    GW->>IS: POST /itineraries (+ X-Correlation-ID, Authorization)

    IS->>AS: Validar aeropuerto de salida
    IS->>AS: Validar aeropuerto de llegada

    alt Aeropuertos válidos (200)
        IS->>DB: INSERT itinerario + INSERT outbox_events y COMMIT
        Note over IS,DB: Una sola transacción (Transactional Outbox, Fase 5):<br/>se guardan los dos o ninguno
        DB-->>IS: Confirmación
        IS-->>GW: 201 Itinerario creado
        GW-->>FE: Respuesta HTTP
        FE-->>Usuario: Mostrar resultado

        R->>DB: Leer pendientes (FOR UPDATE SKIP LOCKED)
        R->>MQ: Publicar ItineraryCreatedEvent
        alt RabbitMQ confirma
            MQ-->>R: Confirm (ack)
            R->>DB: Marcar published_at y COMMIT
        else RabbitMQ no disponible
            R->>DB: attempts + 1 y COMMIT
            Note over R,DB: El evento sigue pendiente:<br/>se reintenta en el siguiente ciclo
        end

        MQ->>TR: Entregar evento (asíncrono, ACK manual)
        TR->>NF: Invocar handler(event, context)
        NF->>NH: INSERT ... ON CONFLICT (event_id) DO NOTHING
        alt event_id nuevo
            NF->>NF: Simular la notificación
            NF->>NH: COMMIT
            NF-->>TR: PROCESSED
        else event_id repetido
            NF-->>TR: ALREADY_PROCESSED
        end
        TR->>MQ: ACK (el mensaje se borra de la cola)
    else Aeropuerto no encontrado (404 de Airport Service)
        IS-->>GW: 422 AIRPORT_NOT_FOUND
        GW-->>FE: Respuesta de error
        FE-->>Usuario: Mostrar error
    else Airport Service no disponible (503)
        IS-->>GW: 503 AIRPORT_SERVICE_UNAVAILABLE
        GW-->>FE: Respuesta de error
        FE-->>Usuario: Mostrar error
    else Airport Service timeout (504)
        IS-->>GW: 504 AIRPORT_SERVICE_TIMEOUT
        GW-->>FE: Respuesta de error
        FE-->>Usuario: Mostrar error
    end
```

**Nota:** desde la Fase 5 la solicitud HTTP no publica en RabbitMQ: guarda el itinerario y su evento en la misma transacción y responde 201. El Outbox Relay, un proceso aparte, publica el evento después y lo reintenta si RabbitMQ no está disponible (ADR-025, ADR-026). La entrega es "al menos una vez": puede haber duplicados, y la función es idempotente con `event_id` (ADR-030). En la Fase 4 la publicación era directa, tras el commit (ADR-022), y un fallo de RabbitMQ perdía el evento. El detalle está en `docs/04-comunicacion-y-eventos.md` (secciones 6 a 8), la topología de RabbitMQ en la sección 3.3 y el contrato en `docs/asyncapi/asyncapi.yaml`. Los fallos del lado del consumidor (función o base de datos caídas, evento inválido, reprocesamiento de la DLQ) están en la sección 3.1.

## 3.1. Fallos en el consumidor: reintentos, DLQ y reprocesamiento (Fase 6)

```mermaid
sequenceDiagram
    participant MQ as RabbitMQ
    participant TR as Event Trigger
    participant NF as SendNotificationFunction
    participant DLQ as DLQ
    actor OP as Equipo

    MQ->>TR: Entregar evento
    alt Función o su base de datos no disponibles
        TR->>NF: Invocar (3 intentos con backoff)
        NF-->>TR: sin conexión / TransientError
        TR->>MQ: basic_nack(requeue=True) tras 10 s
        Note over MQ,TR: Vuelve a la cola: se reintenta sin límite<br/>y nunca va a la DLQ
    else Evento que no cumple el contrato
        TR->>NF: Invocar
        NF-->>TR: REJECTED
        TR->>MQ: basic_reject(requeue=False)
        MQ->>DLQ: x-death: reason=rejected
    else Error de la función (por ejemplo, falta la migración)
        TR->>NF: Invocar (3 intentos con backoff)
        NF-->>TR: errorType=ProgrammingError
        TR->>MQ: basic_reject(requeue=False)
        MQ->>DLQ: x-death: reason=rejected
        OP->>OP: Corregir la causa (alembic upgrade head)
        OP->>DLQ: python -m app.replay_dlq
        DLQ->>MQ: El mensaje vuelve a notification.itinerary-created
        MQ->>TR: Entregar de nuevo → PROCESSED → ACK
    end
```

## 3.2. Recorrido de una solicitud por el API Gateway (Fase 7)

```mermaid
flowchart TD
    REQ[Solicitud al puerto 8000] --> CID["X-Correlation-ID: se reenvía si es válido<br/>o se genera uno con forma de UUID"]
    CID --> PATH{¿Ruta?}
    PATH -->|/health| HEALTH["200 del propio gateway<br/>(no consulta a los servicios)"]
    PATH -->|/| ROOT["Reservada para el frontend (Fase 8)"]
    PATH -->|otra ruta| NF404["404 ROUTE_NOT_FOUND"]
    PATH -->|"/api/airports... o /api/itineraries..."| SIZE{"¿Cuerpo de más de 1 MB?"}
    SIZE -->|sí| R413["413 PAYLOAD_TOO_LARGE"]
    SIZE -->|no| RL{"¿Superó 10 r/s<br/>+ ráfaga de 20?"}
    RL -->|sí| R429["429 RATE_LIMIT_EXCEEDED<br/>Retry-After: 1"]
    RL -->|no| PROXY["Reenviar sin /api, con X-Correlation-ID,<br/>Authorization y X-Forwarded-*"]
    PROXY --> CONN{"¿El servicio acepta<br/>la conexión?"}
    CONN -->|no| R502["502 UPSTREAM_UNAVAILABLE"]
    CONN -->|sí| TIME{"¿Responde dentro<br/>del timeout (15 s)?"}
    TIME -->|no| R504["504 UPSTREAM_TIMEOUT"]
    TIME -->|sí| PASS["Respuesta del servicio SIN cambios<br/>(incluidos sus errores 404, 422, 503...)"]
```

Los errores del gateway (404, 413, 429, 502 y 504) usan el formato único de errores y llevan el mismo `correlation_id` en el cuerpo y en el header. El gateway no reintenta: los reintentos están en los servicios (Fase 2) y reintentar un `POST` podría duplicar un itinerario (ADR-009).

## 4. Flujo de resiliencia de Airport Service

```mermaid
flowchart TD
    A[Solicitud de aeropuerto] --> B{"¿Dato fresco en caché (Redis)?"}
    B -->|Sí| HIT["Devolver resultado (X-Cache: HIT)"]
    B -->|No| C{"¿Circuit breaker permite la llamada?"}
    C -->|"No (OPEN)"| F{"¿Hay copia de respaldo?"}
    C -->|Sí| D["Consultar API Colombia mediante el Adapter, con timeout"]
    D -->|Respuesta válida| G["Guardar copia fresca (10 min) y de respaldo (24 h)"]
    G --> MISS["Devolver resultado (X-Cache: MISS)"]
    D -->|"404 / respuesta inválida"| NR["404 / 502 sin reintentar, sin caché y sin fallback"]
    D -->|"Sin conexión, 5xx o timeout"| R{"¿Quedan intentos?"}
    R -->|Sí| W["Esperar con exponential backoff"] --> D
    R -->|No| CB["Registrar un fallo en el circuit breaker"] --> F
    F -->|Sí| STALE["Fallback: devolver la copia (X-Cache: STALE)"]
    F -->|No| ERR["503, o 504 si fue timeout"]
```

Orden aceptado en la Fase 2 (ADR-014): caché → circuit breaker → retry con backoff → llamada con timeout → fallback. El circuit breaker envuelve al retry, así que una consulta cuenta como un solo fallo cuando se agotaron sus reintentos. Un 404 no se reintenta, no se guarda en caché, no abre el circuito ni activa el fallback.

## 5. Despliegue previsto

```mermaid
flowchart TB
    subgraph Local["Entorno local con Docker Compose"]
        FRONT[Frontend]
        GATE["API Gateway (Nginx)<br/>api-gateway :8000"]
        AIR[Airport Service :8001]
        ITIN[Itinerary Service :8002]
        PG[("PostgreSQL itinerarios<br/>itinerary-postgres :5433")]
        RED[(Redis :6379)]
        RAB["RabbitMQ<br/>itinerary-rabbitmq :5672 / :15672"]
        RELAY["Outbox Relay<br/>(métricas :9101)"]
        TRIG["Event Trigger<br/>(métricas :9102)"]
        FUNC["SendNotificationFunction<br/>imagen Lambda + RIE :9000"]
        NPG[("PostgreSQL notificaciones<br/>notification-postgres :5434")]

        subgraph OBS["Stack de observabilidad (Fase 9)"]
            JAEGER["Jaeger :16686<br/>(OTLP gRPC :4317)"]
            PROM["Prometheus :9090"]
            GRAFANA["Grafana :3000"]
            PROM --> GRAFANA
        end

        FRONT --> GATE
        GATE --> AIR
        GATE --> ITIN
        ITIN --> PG
        ITIN --> AIR
        AIR --> RED
        RELAY --> PG
        RELAY --> RAB
        RAB --> TRIG
        TRIG --> FUNC
        FUNC -->|red notification-net| NPG

        GATE -.->|trazas OTLP gRPC| JAEGER
        AIR -.->|trazas OTLP gRPC| JAEGER
        ITIN -.->|trazas OTLP gRPC| JAEGER
        RELAY -.->|trazas OTLP gRPC| JAEGER
        TRIG -.->|trazas OTLP gRPC| JAEGER
        FUNC -.->|trazas OTLP gRPC| JAEGER
        PROM -.->|scraping /metrics cada 15 s| AIR
        PROM -.->|scraping /metrics cada 15 s| ITIN
        PROM -.->|scraping :9101 cada 15 s| RELAY
        PROM -.->|scraping :9102 cada 15 s| TRIG
    end
```

El despliegue completo se definirá y validará en la Fase 10. Hasta entonces, cada contenedor se crea con `docker run` y los procesos de Python (servicios, relay y trigger) se ejecutan desde su entorno virtual. El gateway (contenedor `api-gateway`) llega a los servicios del equipo por `host.docker.internal`; en la Fase 10 usará los nombres de los contenedores; el orden de arranque está en el `README.md` raíz.

## 5.1. Flujo de datos de observabilidad (Fase 9)

```mermaid
flowchart LR
    subgraph Componentes
        GW["API Gateway<br/>(nginx-otel)"]
        AS[Airport Service]
        IS[Itinerary Service]
        REL[Outbox Relay]
        ET[Event Trigger]
        NF[SendNotificationFunction]
    end

    subgraph Logs
        STDOUT["stdout (JSON)<br/>timestamp · level · service<br/>correlation_id · trace_id · span_id"]
    end

    subgraph Trazas
        JAEGER["Jaeger :16686<br/>OTLP gRPC :4317"]
    end

    subgraph Metricas["Métricas"]
        PROM["Prometheus :9090<br/>scraping cada 15 s"]
        GRAFANA["Grafana :3000<br/>dashboard preconfigurado"]
        PROM --> GRAFANA
    end

    GW -->|"traceparent W3C (ngx_otel_module)"| Trazas
    AS -->|opentelemetry-sdk| Trazas
    IS -->|opentelemetry-sdk| Trazas
    REL -->|opentelemetry-sdk| Trazas
    ET -->|opentelemetry-sdk| Trazas
    NF -->|opentelemetry-sdk| Trazas

    GW --> Logs
    AS --> Logs
    IS --> Logs
    REL --> Logs
    ET --> Logs
    NF --> Logs

    AS -->|"/metrics :8001"| PROM
    IS -->|"/metrics :8002"| PROM
    REL -->|":9101"| PROM
    ET -->|":9102"| PROM
```

El `correlation_id` viaja en el header `X-Correlation-ID` desde el gateway hasta los logs del Outbox Relay y del Event Trigger, y queda guardado en `notification_history`. El `traceparent` W3C une los spans en una sola traza en Jaeger: el gateway lo inyecta, el Itinerary Service lo guarda en `outbox_events` (ADR-037) y el relay lo restaura al publicar en RabbitMQ.

## 6. Consideraciones

- Los diagramas representan el diseño previsto.
- Los nombres de endpoints, colas y contratos deberán coincidir con la implementación final.
- La propiedad de las bases de datos se mantendrá por servicio.
- Los detalles de infraestructura no deberán introducir dependencias directas en el dominio.
