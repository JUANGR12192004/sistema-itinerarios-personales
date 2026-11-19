
# 05. Diagramas arquitectónicos

Todos los diagramas están en Mermaid (GitHub los dibuja directamente) y describen el sistema **tal como está
implementado**: los diagramas de clases salen del código de `app/` de cada componente y el relacional, de las
migraciones de Alembic.

| Sección | Diagrama | Qué responde |
|---|---|---|
| [1](#1-arquitectura-general) | Arquitectura general | ¿Qué piezas hay y cómo se conectan? |
| [2](#2-diagrama-de-componentes) | Componentes | ¿Qué capas y puertos tiene cada componente? |
| [3](#3-diagramas-de-clases) | Clases | ¿Qué clases implementan el dominio, los puertos y los adaptadores? |
| [4](#4-diagrama-relacional) | Relacional | ¿Qué tablas hay y en qué base vive cada una? |
| [5](#5-secuencia-de-creación-de-un-itinerario) | Secuencia | ¿Qué pasa, en orden, al crear un itinerario? (y 5.1 fallos del consumidor, 5.2 gateway) |
| [6](#6-flujo-de-resiliencia-de-airport-service) | Resiliencia | ¿Qué hace Airport Service cuando API Colombia falla? |
| [7](#7-despliegue-con-docker-compose-fase-10) | Despliegue | ¿Qué contenedores, redes y puertos hay? (y 7.1 observabilidad) |

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

El diagrama representa la arquitectura implementada. Los componentes se incorporaron por fases: el gateway llegó en la Fase 7 (Nginx, ADR-009) y el frontend en la Fase 8 (ADR-033), servido por el propio gateway. La llamada Itinerary → Airport es interna y no pasa por el gateway.

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

## 3. Diagramas de clases

Un diagrama por componente con lógica de negocio. Se muestran las clases del dominio, los puertos, los casos de uso y
los adaptadores; se omiten las rutas FastAPI, los esquemas Pydantic de la API y las excepciones.

Cómo leerlos:

| En el diagrama | Significado |
|---|---|
| `«Puerto»` sobre el nombre | Clase abstracta (`ABC`) de la capa `application`: el contrato que usa el caso de uso |
| Línea punteada con punta de triángulo vacío | La clase **implementa** el puerto |
| Flecha continua | La clase **usa** a la otra (la recibe en su constructor) |
| Flecha punteada con punta abierta | La clase **crea o lee** objetos del otro tipo |
| Rombo relleno | Composición: una clase es parte de la otra (`Coordinates` dentro de `Airport`) |
| Rombo vacío con la etiqueta `inner` | El Decorator envuelve a otro objeto del mismo puerto |
| Método subrayado | Método de clase (`@classmethod`), por ejemplo `Itinerary.create(...)` |

Los diagramas se leen de izquierda a derecha: a la izquierda están quienes **usan** o **implementan** (casos de
uso y adaptadores) y a la derecha, aquello de lo que dependen (puertos y dominio). Esa es la **regla de
dependencias** de la arquitectura hexagonal: los casos de uso solo apuntan a puertos y al dominio, los adaptadores de
`infrastructure` apuntan hacia los puertos que implementan y ninguna flecha sale del dominio hacia afuera.

### 3.1. Airport Service: patrón Adapter y Decorators

```mermaid
classDiagram
    direction LR

    class Airport {
        <<Entidad del dominio>>
        +id: int
        +name: str
        +iata_code: str | None
        +oaci_code: str | None
        +type: str
        +city: str
        +department: str
        +coordinates: Coordinates | None
        +has_location() bool
    }
    class Coordinates {
        <<Objeto de valor>>
        +latitude: float
        +longitude: float
    }
    Airport *-- "0..1" Coordinates

    class AirportProvider {
        <<Puerto · Target>>
        +list_airports() list~Airport~
        +get_airport_by_id(airport_id) Airport
    }
    class ListAirports {
        <<Caso de uso · Client>>
        +execute() list~Airport~
    }
    class GetAirportById {
        <<Caso de uso · Client>>
        +execute(airport_id) Airport
    }
    class GetAirportMapData {
        <<Caso de uso · Client>>
        +execute() list~Airport~
    }
    ListAirports --> AirportProvider
    GetAirportById --> AirportProvider
    GetAirportMapData --> AirportProvider

    class ApiColombiaAirportAdapter {
        <<Adapter>>
        +list_airports() list~Airport~
        +get_airport_by_id(airport_id) Airport
    }
    class ApiColombiaClient {
        <<Adaptee>>
        +fetch_airports() JSON
        +fetch_airport(airport_id) JSON | None
    }
    class ApiColombiaAirportDto {
        <<DTO externo · Pydantic>>
        +id: int
        +name: str
        +iata_code: str | None ← iataCode
        +oaci_code: str | None ← oaciCode
        +type: str
        +department_id: int | None ← deparmentId
        +department: name
        +city: name
        +latitude: float
        +longitude: float
    }
    class mapper {
        <<Módulo de traducción>>
        +to_airport(dto) Airport
        +has_swapped_coordinates(dto) bool
    }
    ApiColombiaAirportAdapter ..|> AirportProvider
    ApiColombiaAirportAdapter --> ApiColombiaClient
    ApiColombiaAirportAdapter ..> mapper
    mapper ..> ApiColombiaAirportDto
    mapper ..> Airport

    class ResilientAirportProvider {
        <<Decorator · Fase 2>>
        +list_airports() list~Airport~
        +get_airport_by_id(airport_id) Airport
    }
    class CircuitBreaker {
        +state: CircuitState
        +call(operation)
    }
    class RetryPolicy {
        +run(operation)
        +delay_before_retry(retry_number) float
    }
    ResilientAirportProvider ..|> AirportProvider
    ResilientAirportProvider o-- AirportProvider : inner
    ResilientAirportProvider --> CircuitBreaker
    ResilientAirportProvider --> RetryPolicy

    class CachedAirportProvider {
        <<Decorator · Fase 2>>
        +list_airports() list~Airport~
        +get_airport_by_id(airport_id) Airport
    }
    class CacheStore {
        <<Puerto de infraestructura>>
        +get(key) str | None
        +set(key, value, ttl_seconds)
    }
    class RedisCacheStore
    CachedAirportProvider ..|> AirportProvider
    CachedAirportProvider o-- AirportProvider : inner
    CachedAirportProvider --> CacheStore
    RedisCacheStore ..|> CacheStore
```

| Rol del patrón Adapter | Clase | Capa |
|---|---|---|
| Target (la interfaz que esperan los casos de uso) | `AirportProvider` | `application/ports.py` |
| Client (quien usa el Target) | `ListAirports`, `GetAirportById`, `GetAirportMapData` | `application/use_cases.py` |
| Adapter (traduce la interfaz externa a la interna) | `ApiColombiaAirportAdapter` + funciones de `mapper.py` | `infrastructure/api_colombia/` |
| Adaptee (la interfaz externa incompatible) | `ApiColombiaClient` y el JSON de API Colombia (`ApiColombiaAirportDto`) | `infrastructure/api_colombia/` |

`main.py` (`build_airport_provider`) arma la cadena `CachedAirportProvider(ResilientAirportProvider(ApiColombiaAirportAdapter(ApiColombiaClient)))`.
Los tres implementan el mismo puerto, así que los casos de uso no saben si hay caché ni resiliencia (patrón
Decorator, ADR-007 y ADR-014). `ApiColombiaAirportDto` es el único lugar donde aparece el nombre externo con error
ortográfico (`deparmentId`); `mapper.py` corrige las coordenadas intercambiadas, convierte `"N/A"` en `None` y
deja `coordinates = None` cuando llegan `0, 0` (capa anticorrupción).

### 3.2. Itinerary Service: API

```mermaid
classDiagram
    direction LR

    class Itinerary {
        <<Raíz de agregado>>
        +id: UUID
        +traveler_name: str
        +traveler_email: str | None
        +departure_airport_id: int
        +arrival_airport_id: int
        +travel_date: datetime
        +duration_minutes: int
        +created_at: datetime
        +updated_at: datetime
        +create(...)$ Itinerary
        +update(...) None
    }
    class ItineraryCreatedEvent {
        <<Evento de integración v1>>
        +event_id: UUID
        +occurred_at: datetime
        +correlation_id: str
        +itinerary_id: UUID
        +traveler_name: str
        +traveler_email: str | None
        +departure_airport_id: int
        +arrival_airport_id: int
        +travel_date: datetime
        +duration_minutes: int
        +from_itinerary(itinerary, correlation_id)$ ItineraryCreatedEvent
        +from_dict(payload)$ ItineraryCreatedEvent
        +to_dict() dict
    }
    ItineraryCreatedEvent ..> Itinerary : se construye desde

    class ItineraryRepository {
        <<Puerto>>
        +save(itinerary)
        +get_by_id(itinerary_id) Itinerary | None
        +list_all() list~Itinerary~
        +delete(itinerary_id)
    }
    class AirportCatalog {
        <<Puerto>>
        +verify_exists(airport_id)
    }
    class UnitOfWork {
        <<Puerto>>
        +commit()
    }
    class EventPublisher {
        <<Puerto>>
        +publish(event)
    }

    class CreateItineraryUseCase {
        <<Caso de uso>>
        +execute(command) Itinerary
    }
    class UpdateItineraryUseCase {
        <<Caso de uso>>
        +execute(itinerary_id, command) Itinerary
    }
    class GetItineraryUseCase {
        <<Caso de uso>>
        +execute(itinerary_id) Itinerary
    }
    class ListItinerariesUseCase {
        <<Caso de uso>>
        +execute() list~Itinerary~
    }
    class DeleteItineraryUseCase {
        <<Caso de uso>>
        +execute(itinerary_id)
    }
    CreateItineraryUseCase --> ItineraryRepository
    CreateItineraryUseCase --> AirportCatalog
    CreateItineraryUseCase --> UnitOfWork
    CreateItineraryUseCase --> EventPublisher
    CreateItineraryUseCase ..> ItineraryCreatedEvent : crea
    UpdateItineraryUseCase --> ItineraryRepository
    UpdateItineraryUseCase --> AirportCatalog
    GetItineraryUseCase --> ItineraryRepository
    ListItinerariesUseCase --> ItineraryRepository
    DeleteItineraryUseCase --> ItineraryRepository

    class SqlAlchemyItineraryRepository {
        <<Adaptador · PostgreSQL>>
    }
    class HttpAirportCatalogAdapter {
        <<Adaptador · HTTP>>
        +verify_exists(airport_id)
    }
    class SqlAlchemyUnitOfWork {
        <<Adaptador · PostgreSQL>>
        +commit()
    }
    class OutboxEventPublisher {
        <<Adaptador · Outbox>>
        +publish(event)
    }
    class OutboxMessage {
        <<Aplicación · Fase 5>>
        +id: UUID
        +payload: dict
        +published_at: datetime | None
        +traceparent: str | None
        +from_event(event, traceparent)$ OutboxMessage
    }
    SqlAlchemyItineraryRepository ..|> ItineraryRepository
    HttpAirportCatalogAdapter ..|> AirportCatalog
    SqlAlchemyUnitOfWork ..|> UnitOfWork
    OutboxEventPublisher ..|> EventPublisher
    OutboxEventPublisher ..> OutboxMessage : guarda en outbox_events
    SqlAlchemyItineraryRepository ..> Itinerary : guarda en itineraries
```

`CreateItineraryUseCase` es el caso de uso central: valida los dos aeropuertos con `AirportCatalog`
(`HttpAirportCatalogAdapter` llama a `GET /airports/{id}` de Airport Service), crea el `Itinerary` con
`Itinerary.create(...)` (reglas del dominio), lo guarda, registra el `ItineraryCreatedEvent` con `EventPublisher` y
**después** hace `commit` con `UnitOfWork`. Como `OutboxEventPublisher` usa la misma sesión de SQLAlchemy que el
repositorio, el itinerario y el evento se confirman en la misma transacción (Transactional Outbox, ADR-026).

El evento vive en `application/events.py` y no en el dominio: es un contrato público con otros servicios, no una
regla del negocio (ADR-020). `OutboxMessage` es la fila de `outbox_events` vista desde la aplicación.

### 3.3. Itinerary Service: Outbox Relay

El relay es otro proceso (`python -m app.outbox_relay`) con el mismo código del servicio. Reutiliza los puertos
`EventPublisher` y `UnitOfWork` con otros adaptadores.

```mermaid
classDiagram
    direction LR

    class OutboxRelay {
        <<Aplicación>>
        -batch_size: int
        +run_once() RelayResult
    }
    class RelayResult {
        +published: int
        +failed: int
        +dead: int
    }
    class OutboxRepository {
        <<Puerto>>
        +get_pending(limit) list~OutboxMessage~
        +mark_published(message_id, published_at)
        +mark_failed(message_id, error)
        +mark_dead(message_id, failed_at, error)
    }
    class EventPublisher {
        <<Puerto>>
        +publish(event)
    }
    class UnitOfWork {
        <<Puerto>>
        +commit()
    }
    class OutboxMessage {
        <<Aplicación>>
        +id: UUID
        +payload: dict
        +attempts: int
        +failed_at: datetime | None
        +traceparent: str | None
    }
    class ItineraryCreatedEvent {
        <<Evento de integración v1>>
        +from_dict(payload)$ ItineraryCreatedEvent
    }
    OutboxRelay --> OutboxRepository
    OutboxRelay --> EventPublisher
    OutboxRelay --> UnitOfWork
    OutboxRelay ..> RelayResult : devuelve
    OutboxRepository ..> OutboxMessage
    OutboxRelay ..> ItineraryCreatedEvent : reconstruye desde payload

    class SqlAlchemyOutboxRepository {
        <<Adaptador · PostgreSQL>>
        FOR UPDATE SKIP LOCKED
    }
    class RabbitMQEventPublisher {
        <<Adaptador · RabbitMQ>>
        exchange itinerary.events
        routing key itinerary.created
        +publish(event)
    }
    class SqlAlchemyUnitOfWork {
        <<Adaptador · PostgreSQL>>
        +commit()
    }
    SqlAlchemyOutboxRepository ..|> OutboxRepository
    RabbitMQEventPublisher ..|> EventPublisher
    SqlAlchemyUnitOfWork ..|> UnitOfWork
```

En cada ciclo, `run_once` lee hasta `batch_size` pendientes, reconstruye cada evento con
`ItineraryCreatedEvent.from_dict`, lo publica y lo marca (`mark_published`); si RabbitMQ falla, `mark_failed` y se
detiene el lote; si el mensaje es ilegible, `mark_dead` y sigue con el siguiente (ADR-025, ADR-027). Al final hace
un solo `commit`.

### 3.4. SendNotificationFunction

```mermaid
classDiagram
    direction LR

    class handler {
        <<Adaptador de entrada · Lambda>>
        +handler(event, context) dict
        +process_event(event, run) dict
    }
    class ItineraryCreatedEventSchema {
        <<Esquema Pydantic del contrato v1>>
        +parse_event(raw) ItineraryCreatedEvent
    }
    class ItineraryCreatedEvent {
        <<Aplicación · solo lectura>>
        +event_id: UUID
        +correlation_id: str
        +itinerary_id: UUID
        +traveler_name: str
        +traveler_email: str | None
        +departure_airport_id: int
        +arrival_airport_id: int
        +travel_date: datetime
        +duration_minutes: int
    }
    handler ..> ItineraryCreatedEventSchema : valida
    ItineraryCreatedEventSchema ..> ItineraryCreatedEvent : crea
    handler --> NotifyItineraryCreatedUseCase

    class NotifyItineraryCreatedUseCase {
        <<Caso de uso>>
        +execute(event) NotificationResult
    }
    class NotificationResult {
        +status: ProcessingStatus
        +event_id: UUID
        +notification_id: UUID | None
        +notification_status: NotificationStatus | None
    }
    class ProcessingStatus {
        <<enumeration>>
        PROCESSED
        ALREADY_PROCESSED
        REJECTED
    }
    NotifyItineraryCreatedUseCase ..> NotificationResult : devuelve
    NotificationResult --> ProcessingStatus

    class NotificationRecord {
        <<Entidad del dominio>>
        +id: UUID
        +event_id: UUID
        +itinerary_id: UUID
        +recipient: str | None
        +channel: str
        +message: str
        +status: NotificationStatus
        +status_reason: str | None
        +correlation_id: str | None
        +processed_at: datetime
        +create(...)$ NotificationRecord
        +should_be_sent() bool
    }
    class NotificationStatus {
        <<enumeration>>
        SENT
        SKIPPED
    }
    NotificationRecord --> NotificationStatus
    NotifyItineraryCreatedUseCase ..> NotificationRecord : crea

    class NotificationHistoryRepository {
        <<Puerto>>
        +add_if_absent(record) bool
    }
    class NotificationSender {
        <<Puerto>>
        +send(recipient, message)
    }
    class UnitOfWork {
        <<Puerto>>
        +commit()
    }
    NotifyItineraryCreatedUseCase --> NotificationHistoryRepository
    NotifyItineraryCreatedUseCase --> NotificationSender
    NotifyItineraryCreatedUseCase --> UnitOfWork

    class SqlAlchemyNotificationHistoryRepository {
        <<Adaptador · PostgreSQL>>
        INSERT ... ON CONFLICT DO NOTHING
    }
    class SimulatedEmailSender {
        <<Adaptador · correo simulado>>
    }
    class SqlAlchemyUnitOfWork {
        <<Adaptador · PostgreSQL>>
    }
    SqlAlchemyNotificationHistoryRepository ..|> NotificationHistoryRepository
    SimulatedEmailSender ..|> NotificationSender
    SqlAlchemyUnitOfWork ..|> UnitOfWork
```

`handler` y `parse_event` son funciones (no clases), pero cumplen el papel de adaptador de entrada: igual que una
ruta FastAPI, reciben la entrada de la plataforma, la convierten al modelo de la aplicación y llaman al caso de uso
(ADR-028). Un evento que no cumple el contrato produce `InvalidEventError` y la respuesta `REJECTED`; un fallo de
PostgreSQL produce `TransientError`.

El caso de uso es **idempotente**: `add_if_absent` inserta con `ON CONFLICT (event_id) DO NOTHING` y devuelve
`False` si el evento ya estaba; en ese caso responde `ALREADY_PROCESSED` sin volver a enviar (ADR-030). La función
tiene su **propia** clase `ItineraryCreatedEvent`: no importa código de Itinerary Service, solo comparten el contrato
publicado en AsyncAPI.

## 4. Diagrama relacional

El sistema tiene **dos bases de datos PostgreSQL independientes**, cada una propiedad de un solo componente
(ADR-004, ADR-016, ADR-029). Airport Service no tiene base relacional: su fuente de verdad es API Colombia y solo
usa Redis como caché. Las tablas salen de las migraciones de Alembic (`services/itinerary-service/alembic/versions/`
y `serverless/send-notification-function/alembic/versions/`); cada base tiene además la tabla `alembic_version`,
que Alembic usa para saber qué migración está aplicada.

### 4.1. `itinerary_db` (Itinerary Service, contenedor `itinerary-postgres`, puerto 5433)

```mermaid
erDiagram
    itineraries {
        uuid id PK
        varchar traveler_name "NOT NULL, 255"
        varchar traveler_email "NULL, 255"
        integer departure_airport_id "NOT NULL, id del catálogo"
        integer arrival_airport_id "NOT NULL, id del catálogo"
        timestamptz travel_date "NOT NULL"
        integer duration_minutes "NOT NULL"
        timestamptz created_at "NOT NULL"
        timestamptz updated_at "NOT NULL"
    }
    outbox_events {
        uuid id PK "= event_id del evento"
        varchar aggregate_type "NOT NULL, itinerary"
        uuid aggregate_id "NOT NULL, id del itinerario"
        varchar event_type "NOT NULL, itinerary.created"
        integer event_version "NOT NULL, 1"
        jsonb payload "NOT NULL, evento completo"
        timestamptz occurred_at "NOT NULL"
        timestamptz published_at "NULL mientras está pendiente"
        integer attempts "NOT NULL, DEFAULT 0"
        text last_error "NULL"
        timestamptz failed_at "NULL, fallo permanente"
        varchar traceparent "NULL, 55, contexto W3C"
    }
    itineraries |o..o| outbox_events : "aggregate_id (sin clave foránea)"
```

| Migración | Qué hace |
|---|---|
| `a3f1e2b4c5d0` (Fase 3) | Crea `itineraries` |
| `b7c2d9e1f4a6` (Fase 5) | Crea `outbox_events` y el índice parcial `ix_outbox_events_pending` |
| `c4d8e2f6a9b1` (Fase 5) | Agrega `failed_at` y redefine el índice parcial (ADR-027) |
| `e6f0a4b8c1d9` (Fase 9) | Agrega `traceparent` (ADR-037) |

- **Índice parcial `ix_outbox_events_pending`** sobre `occurred_at`, solo con las filas
  `published_at IS NULL AND failed_at IS NULL`: contiene únicamente los eventos pendientes, que son los que busca el
  relay en orden de llegada. Los eventos publicados se conservan, pero no ocupan el índice.
- **Sin clave foránea entre `outbox_events` y `itineraries`.** Cada itinerario creado tiene un evento
  (`aggregate_id` = `itineraries.id`), pero la relación es lógica: al borrar un itinerario su evento se conserva,
  porque el evento describe algo que ya ocurrió y puede estar pendiente de publicar.
- **Los aeropuertos se referencian por id** (`departure_airport_id`, `arrival_airport_id`): el catálogo vive en otro
  contexto (Airport Service), así que no hay tabla de aeropuertos ni clave foránea (CLAUDE.md, sección 8.1).

### 4.2. `notification_db` (SendNotificationFunction, contenedor `notification-postgres`, puerto 5434)

```mermaid
erDiagram
    notification_history {
        uuid id PK
        uuid event_id UK "NOT NULL, clave de idempotencia"
        uuid itinerary_id "NOT NULL, id del itinerario"
        varchar recipient "NULL si no hay correo, 255"
        varchar channel "NOT NULL, simulated-email"
        text message "NOT NULL"
        varchar status "NOT NULL, SENT o SKIPPED"
        text status_reason "NULL, motivo de SKIPPED"
        varchar correlation_id "NULL, 255"
        timestamptz processed_at "NOT NULL"
    }
```

| Migración | Qué hace |
|---|---|
| `d1e5f7a3b9c2` (Fase 6) | Crea `notification_history` con sus dos restricciones |

- **`uq_notification_history_event_id`** (único sobre `event_id`): es lo que hace idempotente a la función. Si el
  mismo evento llega dos veces, el segundo `INSERT ... ON CONFLICT (event_id) DO NOTHING` no inserta nada (ADR-030).
- **`ck_notification_history_status`**: `status IN ('SENT', 'SKIPPED')`.
- **`itinerary_id` está en otra base** (`itinerary_db`): no puede haber clave foránea entre bases. La función solo
  conoce lo que trae el evento.

### 4.3. Referencias entre bases

| Columna | Apunta a | Cómo se mantiene |
|---|---|---|
| `itineraries.departure_airport_id` / `arrival_airport_id` | Aeropuerto de API Colombia (Airport Service) | Itinerary Service lo valida por HTTP antes de guardar |
| `outbox_events.aggregate_id` | `itineraries.id` (misma base) | Se escribe en la misma transacción que el itinerario |
| `notification_history.itinerary_id` | `itineraries.id` (otra base) | Llega en el evento `ItineraryCreatedEvent` |
| `notification_history.event_id` | `outbox_events.id` (otra base) | Es el mismo `event_id` del evento |
| `notification_history.correlation_id` | El `X-Correlation-ID` de la solicitud original | Viaja en el evento |

Ningún servicio lee ni escribe la base de otro (CLAUDE.md, sección 7.2): la única forma de que un dato pase de una
base a la otra es el evento.

## 5. Secuencia de creación de un itinerario

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

**Nota:** desde la Fase 5 la solicitud HTTP no publica en RabbitMQ: guarda el itinerario y su evento en la misma transacción y responde 201. El Outbox Relay, un proceso aparte, publica el evento después y lo reintenta si RabbitMQ no está disponible (ADR-025, ADR-026). La entrega es "al menos una vez": puede haber duplicados, y la función es idempotente con `event_id` (ADR-030). En la Fase 4 la publicación era directa, tras el commit (ADR-022), y un fallo de RabbitMQ perdía el evento. El detalle está en `docs/04-comunicacion-y-eventos.md` (secciones 6 a 8), la topología de RabbitMQ en la sección 3.3 de ese mismo documento y el contrato en `docs/asyncapi/asyncapi.yaml`. Los fallos del lado del consumidor (función o base de datos caídas, evento inválido, reprocesamiento de la DLQ) están en la sección 5.1.

### 5.1. Fallos en el consumidor: reintentos, DLQ y reprocesamiento (Fase 6)

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

### 5.2. Recorrido de una solicitud por el API Gateway (Fase 7)

```mermaid
flowchart TD
    REQ[Solicitud al puerto 8000] --> CID["X-Correlation-ID: se reenvía si es válido<br/>o se genera uno con forma de UUID"]
    CID --> PATH{¿Ruta?}
    PATH -->|/health| HEALTH["200 del propio gateway<br/>(no consulta a los servicios)"]
    PATH -->|"/ y archivos estáticos"| ROOT["Frontend: archivos de frontend/ (Fase 8)<br/>archivo inexistente → 404 ROUTE_NOT_FOUND"]
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

## 6. Flujo de resiliencia de Airport Service

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

## 7. Despliegue con Docker Compose (Fase 10)

Cada caja es un servicio de `docker-compose.yml`; el puerto es el publicado en el equipo. Las bases de datos
solo están en su red (`itinerary-data`, `notification-data`); todo lo demás comparte la red `default` (ADR-041).

```mermaid
flowchart TB
    subgraph Local["docker compose up -d --build (proyecto sistema-itinerarios)"]
        FRONT[Frontend en el navegador]
        GATE["api-gateway (Nginx + frontend) :8000"]
        AIR[airport-service :8001]
        ITIN[itinerary-service :8002]
        RED[(redis :6379)]
        RAB["rabbitmq :5672 / :15672"]
        RELAY["outbox-relay<br/>(misma imagen que itinerary-service, métricas :9101)"]
        TRIG["event-trigger<br/>(métricas :9102)"]
        FUNC["send-notification-function<br/>imagen Lambda + RIE :9000"]

        subgraph IDATA["red itinerary-data"]
            PG[("itinerary-postgres :5433")]
            IMIG["itinerary-migrations<br/>(una sola ejecución)"]
        end

        subgraph NDATA["red notification-data"]
            NPG[("notification-postgres :5434")]
            NMIG["notification-migrations<br/>(una sola ejecución)"]
        end

        IMIG -->|alembic upgrade head| PG
        NMIG -->|alembic upgrade head| NPG

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
        FUNC --> NPG

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

Orden de arranque que impone `depends_on` (las flechas se leen "espera a"):

```mermaid
flowchart LR
    IP[(itinerary-postgres)] -->|healthy| IM[itinerary-migrations]
    IM -->|terminó con éxito| IS[itinerary-service]
    IM -->|terminó con éxito| OR[outbox-relay]
    RMQ[rabbitmq] -->|healthy| OR
    RMQ -->|healthy| ET[event-trigger]
    NP[(notification-postgres)] -->|healthy| NM[notification-migrations]
    NM -->|terminó con éxito| FN[send-notification-function]
    FN -->|iniciado| ET
    R[redis] -->|iniciado| AS[airport-service]
    AS -->|iniciado| GW[api-gateway]
    IS -->|iniciado| GW
    J[jaeger] -->|iniciado| GW
    P[prometheus] -->|iniciado| G[grafana]
```

Hasta la Fase 9 cada contenedor se creaba con `docker run` y los procesos de Python se ejecutaban desde su entorno virtual, con el gateway llegando a ellos por `host.docker.internal`. Ese modo manual sigue documentado en [`07-ejecucion-manual.md`](07-ejecucion-manual.md) para desarrollar un componente con recarga automática.

### 7.1. Flujo de datos de observabilidad (Fase 9)

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

## 8. Consideraciones

- Los diagramas representan el sistema implementado al cierre del proyecto (Fase 12): los de clases salen del código de `app/` y el relacional, de las migraciones de Alembic. Si el código cambia, el diagrama afectado se actualiza en el mismo pull request.
- Los nombres de endpoints, colas y contratos coinciden con la implementación; los contratos los verifican las pruebas de contrato (`docs/openapi/airport-service.json` y `docs/asyncapi/asyncapi.yaml`, ADR-042).
- Cada base de datos pertenece a un solo componente (ADR-004, ADR-029); en Docker Compose, cada una está además en su propia red (ADR-041).
- El dominio no depende de la infraestructura: ninguna flecha de los diagramas de clases sale del dominio (regla de dependencias, ADR-002).
- El `README.md` raíz incluye copias de los diagramas de secuencia, relacional y despliegue: si uno cambia, se actualiza en los dos lugares.
