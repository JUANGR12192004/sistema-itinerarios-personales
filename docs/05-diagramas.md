
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
        MSGADAPTER[Messaging Adapter]

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
    AS-->>IS: Resultado de validación

    IS->>AS: Validar aeropuerto de llegada
    AS-->>IS: Resultado de validación

    alt Aeropuertos válidos
        IS->>DB: Guardar itinerario
        Note over IS,DB: En la fase Outbox se guardarán<br/>itinerario y evento en una transacción
        DB-->>IS: Confirmación
        IS-->>GW: Itinerario creado
        GW-->>FE: Respuesta HTTP
        FE-->>Usuario: Mostrar resultado

        IS->>MQ: Publicar evento
        MQ-->>NF: Entregar evento
        NF->>NF: Simular notificación
        NF->>NF: Registrar historial
    else Aeropuerto inválido
        IS-->>GW: Error de validación
        GW-->>FE: Respuesta HTTP de error
        FE-->>Usuario: Mostrar error
    end
```

**Nota:** el diagrama muestra el flujo lógico objetivo. La confirmación de la solicitud HTTP y el procesamiento de la notificación son independientes. La publicación directa ilustrada se sustituirá por el mecanismo Outbox cuando se implemente la Fase 5.

## 4. Flujo de resiliencia de Airport Service

```mermaid
flowchart TD
    A[Solicitud de aeropuerto] --> B{¿Existe en caché?}
    B -->|Sí| C[Devolver resultado]
    B -->|No| D[Consultar proveedor mediante Adapter]
    D --> E{¿Respuesta válida?}
    E -->|Sí| F[Guardar en caché cuando corresponda]
    F --> C
    E -->|No| G[Aplicar timeout y política de retry]
    G --> H{¿Circuit Breaker permite la llamada?}
    H -->|No| I[Aplicar fallback si es válido]
    H -->|Sí| J[Ejecutar llamada controlada]
    J --> K{¿Resultado satisfactorio?}
    K -->|Sí| F
    K -->|No| I
```

Este diagrama representa mecanismos previstos para la Fase 2; no significa que ya estén implementados ni establece por sí solo el orden exacto de los componentes de resiliencia.

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
