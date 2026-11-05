
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

    IS --> DBI[(PostgreSQL de itinerarios)]
    IS --> OUTBOX[Transactional Outbox]

    OUTBOX --> PUB[Worker / Publisher]
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
        MSGADAPTER[RabbitMQEventPublisher]

        IC --> UC
        UC --> DOMAIN
        UC --> REPO
        UC --> CATALOG
        UC --> PUBPORT
        PERSIST -.->|implements| REPO
        HTTPADAPTER -.->|implements| CATALOG
        MSGADAPTER -.->|implements| PUBPORT
    end

    DB[(PostgreSQL)] <--> PERSIST
    HTTPADAPTER -->|"HTTP GET /airports/{id}"| AC
    MSGADAPTER -->|publicación de evento| MQ[RabbitMQ]
    MQ --> NF[SendNotificationFunction]
```

Las flechas punteadas representan una relación de implementación conceptual de los puertos, no una llamada en tiempo de ejecución.

Itinerary Service no accede a las capas internas de Airport Service: el adaptador `HttpAirportCatalogAdapter` llama a su API REST. Los casos de uso tampoco hablan directamente con RabbitMQ: usan el puerto `EventPublisher`, implementado en la Fase 4 por un publicador de RabbitMQ y en la Fase 5 por un adaptador Outbox (ADR-013).

## 3. Secuencia de creación de un itinerario

```mermaid
sequenceDiagram
    actor Usuario
    participant FE as Frontend
    participant GW as API Gateway
    participant IS as Itinerary Service
    participant AS as Airport Service
    participant DB as PostgreSQL
    participant MQ as RabbitMQ
    participant NF as SendNotificationFunction

    Usuario->>FE: Crear itinerario
    FE->>GW: POST /itineraries
    GW->>IS: Reenviar solicitud

    IS->>AS: Validar aeropuerto de salida
    IS->>AS: Validar aeropuerto de llegada

    alt Aeropuertos válidos (200)
        IS->>DB: Guardar itinerario y COMMIT
        Note over IS,DB: En la fase Outbox se guardarán<br/>itinerario y evento en una transacción
        DB-->>IS: Confirmación
        IS->>MQ: Publicar ItineraryCreatedEvent (Fase 4: tras el commit)
        alt RabbitMQ confirma
            MQ-->>IS: Confirm (ack)
        else RabbitMQ no disponible
            Note over IS,MQ: Log ERROR "Evento perdido" (double write).<br/>El itinerario ya existe: igual se responde 201
        end
        IS-->>GW: 201 Itinerario creado
        GW-->>FE: Respuesta HTTP
        FE-->>Usuario: Mostrar resultado

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

**Nota:** en la Fase 4 la publicación es directa y ocurre dentro de la solicitud, después del commit y antes de responder (ADR-022). El procesamiento de la notificación sí es independiente de la respuesta HTTP. La publicación directa se sustituirá por el mecanismo Outbox en la Fase 5. La topología de RabbitMQ está en `docs/04-comunicacion-y-eventos.md` (sección 3.3) y el contrato en `docs/asyncapi/asyncapi.yaml`.

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
