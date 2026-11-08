
# 05. Diagramas arquitectónicos

## 1. Arquitectura general

```mermaid
flowchart TB
    U[Usuario] --> FE[Frontend]
    FE --> GW[API Gateway / BFF]

    GW --> AS[Airport Service]
    GW --> IS[Itinerary Service]

    IS -->|HTTP: validar aeropuertos| AS
    AS --> AD[API Colombia Adapter]
    AD --> EXT[API Colombia]

    AS -.-> REDIS[(Redis)]

    IS --> DBI[(PostgreSQL de itinerarios<br/>itineraries + outbox_events)]
    DBI --> PUB[Outbox Relay]
    PUB --> RMQ[RabbitMQ]

    RMQ --> NS[Sistema de notificaciones]
    NS --> FN[SendNotificationFunction]
    FN --> NH[(Historial de notificaciones)]

    FE --> MAP[Plotly JS]
```

El diagrama representa la arquitectura objetivo. Los componentes se incorporarán progresivamente, no todos desde la Fase 0.

La persistencia del historial de notificaciones se representa de forma conceptual; la tecnología definitiva queda pendiente de selección.

## 2. Diagrama de componentes

```mermaid
flowchart LR
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
    MSGADAPTER -->|publicación de evento| MQ[RabbitMQ]
    MQ --> NF[SendNotificationFunction]
```

Las flechas punteadas representan una relación de implementación conceptual de los puertos, no una llamada en tiempo de ejecución.

Itinerary Service no accede a las capas internas de Airport Service: el adaptador `HttpAirportCatalogAdapter` llama a su API REST. Los casos de uso tampoco hablan directamente con RabbitMQ: usan el puerto `EventPublisher`, implementado en la Fase 4 por un publicador de RabbitMQ y en la Fase 5 por un adaptador Outbox, que registra el evento antes del commit, en la misma transacción del itinerario (ADR-013, ADR-026).

El mismo puerto `EventPublisher` tiene dos adaptadores, uno en cada proceso: en la API, `OutboxEventPublisher` guarda el evento en `outbox_events`; en el Outbox Relay, `RabbitMQEventPublisher` (el de la Fase 4, sin cambios) lo publica en RabbitMQ. El relay lee y marca los pendientes con su propio puerto, `OutboxRepository` (ADR-025).

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
    participant NF as SendNotificationFunction

    Usuario->>FE: Crear itinerario
    FE->>GW: POST /itineraries
    GW->>IS: Reenviar solicitud

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

        MQ-->>NF: Entregar evento (asíncrono, Fase 6)
        NF->>NF: Simular notificación
        NF->>NF: Registrar historial
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

**Nota:** desde la Fase 5 la solicitud HTTP no publica en RabbitMQ: guarda el itinerario y su evento en la misma transacción y responde 201. El Outbox Relay, un proceso aparte, publica el evento después y lo reintenta si RabbitMQ no está disponible (ADR-025, ADR-026). La entrega es "al menos una vez": puede haber duplicados y el consumidor debe ser idempotente con `event_id`. En la Fase 4 la publicación era directa, tras el commit (ADR-022), y un fallo de RabbitMQ perdía el evento. El detalle está en `docs/04-comunicacion-y-eventos.md` (secciones 6 y 7), la topología de RabbitMQ en la sección 3.3 y el contrato en `docs/asyncapi/asyncapi.yaml`.

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
        GATE[API Gateway]
        AIR[Airport Service]
        ITIN[Itinerary Service]
        PG[(PostgreSQL)]
        RED[(Redis)]
        RAB[RabbitMQ]
        NOTIF[Función serverless / adaptador]
        OBS[Stack de observabilidad]

        FRONT --> GATE
        GATE --> AIR
        GATE --> ITIN
        ITIN --> PG
        ITIN --> AIR
        AIR --> RED
        ITIN --> RAB
        RAB --> NOTIF
    end
```

El despliegue completo se definirá y validará en la Fase 10. La integración de observabilidad se desarrollará en la Fase 9.

## 6. Consideraciones

- Los diagramas representan el diseño previsto.
- Los nombres de endpoints, colas y contratos deberán coincidir con la implementación final.
- La propiedad de las bases de datos se mantendrá por servicio.
- Los detalles de infraestructura no deberán introducir dependencias directas en el dominio.
