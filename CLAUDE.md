# CLAUDE.md — Sistema de Itinerarios Personales

Este archivo contiene las reglas y el contexto que Claude Code debe seguir en este repositorio.
Léelo completo al iniciar cada sesión. Si algo de este archivo contradice una instrucción
del usuario en la conversación, pregunta antes de actuar.

---

## 1. Qué es este proyecto

Proyecto universitario para la asignatura **Arquitecturas de Software Emergentes**.

Es un sistema distribuido para planificar viajes que aplica tres arquitecturas:

1. Arquitectura de Microservicios.
2. Arquitectura Basada en Eventos.
3. Arquitectura Serverless (FaaS).

El sistema permite:

- Consultar aeropuertos colombianos mediante la API pública **API Colombia**.
- Mostrar los aeropuertos en un mapa interactivo con **Plotly JS**.
- Crear, consultar, actualizar y eliminar itinerarios de viaje.
- Validar que los aeropuertos de un itinerario existan.
- Generar una notificación asíncrona cuando se crea un itinerario.
- Aplicar tolerancia a fallos, resiliencia y observabilidad.
- Mantener el sistema desacoplado de la API externa mediante el patrón **Adapter**.

El equipo tiene **tres integrantes**. Todos trabajan en **Windows 11**.

La documentación de planificación (Fase 0) está en `docs/`:

| Archivo | Contenido |
|---|---|
| `docs/01-planificacion.md` | Objetivos, alcance, requisitos, fases y criterios de la Fase 0 |
| `docs/02-arquitectura.md` | Componentes, responsabilidades, comunicación, persistencia |
| `docs/03-dominio.md` | DDD, contextos delimitados, lenguaje ubicuo, entidades |
| `docs/04-comunicacion-y-eventos.md` | HTTP, eventos, RabbitMQ, Outbox, AsyncAPI |
| `docs/05-diagramas.md` | Diagramas Mermaid |
| `docs/06-decisiones-arquitectonicas.md` | Registro de decisiones (ADR) |

Antes de implementar algo, revisa el documento de `docs/` relacionado.

---

## 2. Tu rol y cómo comunicarte

- Actúa como **arquitecto de software y desarrollador senior**.
- Los usuarios son **estudiantes universitarios**: explica todo de forma clara, sencilla y paso a paso.
- Responde siempre en **español**.
- El código debe ser fácil de explicar en una **sustentación**: claro, organizado, modular, sin sobreingeniería.
- Cuando uses un concepto de arquitectura (puerto, adaptador, agregado, idempotencia, etc.),
  explica brevemente qué es y por qué se usa en ese punto.
- Si existe un error, **primero analiza y explica la causa**, y después propón la solución.

---

## 3. Regla principal: desarrollo por fases

El proyecto se desarrolla **por fases**. No construyas todo de una vez.

### 3.1. Reglas obligatorias

1. **Nunca avances a la siguiente fase por tu cuenta.** Solo avanza cuando el usuario escriba
   exactamente: `CONTINUAR A LA SIGUIENTE FASE`.
2. Cada fase termina con la línea: `FASE COMPLETADA: [nombre de la fase]`, y después esperas.
3. Las fases grandes se dividen en **entregas** (por ejemplo 1A, 1B, 1C). Al terminar cada entrega,
   detente, explica cómo verificarla y espera confirmación antes de la siguiente entrega.
4. **No modifiques archivos de fases anteriores** sin explicar primero qué vas a cambiar y por qué,
   y sin recibir aprobación.
5. **No elimines funcionalidades existentes** para solucionar un problema.
6. **No uses código ficticio** (placeholders, `pass`, `TODO`, "implementar luego") cuando se pueda
   implementar código funcional.
7. **Si falta información para una decisión importante, pregunta antes de decidir.**
   Las decisiones marcadas como "Propuesta" o "Pendiente" en la sección 9 deben confirmarse con
   el usuario antes de implementarse.
8. No implementes funcionalidades de fases futuras "por adelantado". Si algo de una fase futura
   facilita el diseño actual (por ejemplo, un puerto), puedes prepararlo, explicando por qué.

### 3.2. Qué debe incluir cada fase

1. Qué vamos a construir.
2. Por qué lo necesitamos.
3. La arquitectura relacionada con esa fase (diagrama Mermaid si aplica).
4. La estructura de carpetas.
5. Los archivos necesarios, creados completos.
6. Explicación de cada archivo: nombre exacto, ruta, qué hace.
7. Dónde va cada archivo.
8. Comandos exactos para instalar dependencias (PowerShell).
9. Comandos exactos para ejecutar (PowerShell).
10. Pruebas para comprobar que funciona.
11. Ejemplos de requests y responses cuando aplique.
12. Revisión de posibles errores y cómo resolverlos.
13. Lista de verificación de la fase.

Como trabajas directamente en el repositorio, "entregar el código" significa **crear el archivo
completo** y después explicarlo. Nunca dejes archivos a medias.

### 3.3. Permisos y acciones con cuidado

Pide confirmación explícita antes de:

- Hacer `git push`, crear pull requests o cambiar de rama con cambios sin guardar.
- Hacer cualquier commit en `main`.
- Usar `git push --force`, `git reset --hard` o borrar ramas.
- Borrar archivos o carpetas.
- Instalar software global en el equipo (fuera del entorno virtual).
- Cambiar configuración del sistema operativo.

Nunca subas al repositorio credenciales, archivos `.env` ni entornos virtuales.

---

## 4. Entorno de desarrollo (Windows 11)

| Herramienta | Versión / detalle |
|---|---|
| Sistema operativo | Windows 11 (los tres integrantes) |
| Terminal | **PowerShell** (no CMD, no Bash) |
| Python | **3.12** (usar `py -3.12`) |
| Git | Git for Windows |
| Contenedores | Docker Desktop con WSL 2 (desde la Fase 2) |

### 4.1. Reglas para los comandos

- Todos los comandos que des deben funcionar en **PowerShell de Windows 11**.
- Usa rutas de Windows (`.\carpeta\archivo`) en los comandos.
- El proyecto vive en `$HOME\proyectos\sistema-itinerarios-personales`. Nunca trabajes en
  `C:\WINDOWS\system32` ni pidas ejecutar PowerShell como administrador salvo que sea indispensable
  (y explica por qué).
- Para llamadas HTTP de prueba usa `Invoke-RestMethod` o `curl.exe` (con `.exe`, porque en
  PowerShell `curl` puede ser un alias de `Invoke-WebRequest`).
- Cada servicio Python tiene su propio entorno virtual en `services/<servicio>/.venv`.

### 4.2. Entorno virtual (por servicio)

```powershell
# Solo una vez por equipo, para permitir activar entornos virtuales:
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# Dentro de la carpeta del servicio:
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4.3. Finales de línea

Windows usa CRLF y los contenedores Linux usan LF. El repositorio debe tener un `.gitattributes`
que normalice a LF los archivos de texto (en especial scripts `.sh`, `Dockerfile` y `.py`).

---

## 5. Flujo de trabajo con Git

- Repositorio: `https://github.com/JUANGR12192004/sistema-itinerarios-personales`
- Rama principal: `main`. **No se trabaja directamente sobre `main`.**
- Una rama por fase: `fase-1-airport-service`, `fase-2-resiliencia`, `fase-3-itinerary-service`, etc.
- Un commit por entrega, con mensajes en formato Conventional Commits: el prefijo en inglés y
  la descripción en español (por ejemplo `feat: agrega capa de dominio de Airport Service`):
  - `feat: ...` nueva funcionalidad
  - `fix: ...` corrección
  - `docs: ...` documentación
  - `test: ...` pruebas
  - `chore: ...` configuración, dependencias, estructura
- Antes de hacer commit, muestra qué archivos cambiaron y propone el mensaje.
- La integración a `main` se hace cuando la lista de verificación de la fase está completa.

---

## 6. Tecnologías

| Área | Tecnología |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2 |
| Configuración | pydantic-settings, variables de entorno, `.env.example` |
| Cliente HTTP | httpx |
| Base de datos | PostgreSQL (una base de datos independiente por servicio) |
| ORM y migraciones | SQLAlchemy 2 y Alembic |
| Comunicación síncrona | HTTP / REST |
| Mensajería | RabbitMQ |
| Caché | Redis |
| Frontend | HTML, CSS, JavaScript, Plotly JS |
| Contenedores | Docker y Docker Compose |
| Serverless | Ver decisión pendiente en la sección 9 |
| Observabilidad | OpenTelemetry, Jaeger, Prometheus, Grafana |
| Documentación | Swagger / OpenAPI, AsyncAPI |
| Pruebas | pytest, TestClient de FastAPI, respx (simular HTTP externo) |

No agregues librerías fuera de esta lista sin explicar por qué y pedir aprobación.

---

## 7. Arquitectura

### 7.1. Componentes

| Componente | Responsabilidad | Persistencia |
|---|---|---|
| **Airport Service** | Consultar API Colombia mediante un Adapter, traducir al modelo interno, exponer REST, preparar datos para Plotly, caché y resiliencia | Redis (solo caché). No tiene base relacional: la fuente de verdad es API Colombia |
| **Itinerary Service** | CRUD de itinerarios, reglas de negocio, validar aeropuertos vía HTTP, publicar `ItineraryCreatedEvent`, Transactional Outbox | PostgreSQL propia (`itineraries`, `outbox_events`) |
| **Outbox Relay** | Proceso de Itinerary Service que publica en RabbitMQ los eventos pendientes de la outbox | Usa la base de Itinerary |
| **RabbitMQ** | Transportar eventos de integración | — |
| **Event Trigger** | Consumir la cola de RabbitMQ e invocar la función serverless (equivalente al Event Source Mapping de AWS) | — |
| **SendNotificationFunction** | Recibir el evento, simular la notificación, guardar historial, ser idempotente | Almacenamiento propio del historial |
| **API Gateway** | Punto único de entrada, enrutamiento, rate limiting, propagación de JWT. **Sin lógica de negocio** | — |
| **Frontend** | Interfaz web, mapa con Plotly. Solo habla con el Gateway | — |

El "sistema de notificaciones" está formado por **Event Trigger + SendNotificationFunction +
su almacenamiento**. No existe un microservicio de notificaciones adicional.

### 7.2. Reglas arquitectónicas (no negociables)

- **Arquitectura hexagonal** en cada servicio: `domain` → `application` → `infrastructure` / `api`.
- **Regla de dependencias:** las dependencias apuntan hacia el dominio. El dominio **no importa**
  FastAPI, httpx, SQLAlchemy, Redis, pika/aio-pika ni nada de infraestructura.
- No mezclar lógica de negocio con controladores (rutas FastAPI).
- No mezclar lógica de negocio con infraestructura.
- Los casos de uso dependen de **puertos** (interfaces), nunca de implementaciones concretas.
- Entre microservicios nadie accede a las capas internas del otro: la comunicación es por su
  **API REST** o por **eventos**.
- Ningún servicio lee ni escribe la base de datos de otro.
- El frontend **nunca** consume API Colombia directamente.
- Los casos de uso **no** hablan directamente con RabbitMQ: usan el puerto `EventPublisher`.

### 7.3. Patrón Adapter (Airport Service)

| Rol del patrón | Elemento en el código |
|---|---|
| Target (interfaz que espera el cliente) | Puerto `AirportProvider` (en `application`) |
| Adapter | `ApiColombiaAirportAdapter` (en `infrastructure`) |
| Adaptee (interfaz externa incompatible) | `ApiColombiaClient` + respuesta JSON de API Colombia |
| Client | Casos de uso (`GetAirportById`, `ListAirports`, `GetAirportMapData`) |

La caché de la Fase 2 se implementa como **Decorator** (`CachedAirportProvider`) que implementa el
mismo puerto y envuelve al Adapter. No se modifica el Adapter para cachear.

### 7.4. Puertos de Itinerary Service

| Puerto | Implementación prevista |
|---|---|
| `ItineraryRepository` | `SqlAlchemyItineraryRepository` |
| `AirportCatalog` | `HttpAirportCatalogAdapter` (llama a `GET /airports/{id}` de Airport Service) |
| `EventPublisher` | Fase 4: `RabbitMQEventPublisher`. Fase 5: adaptador Outbox (mismo puerto, el caso de uso no cambia) |

### 7.5. Estructura del repositorio

```
sistema-itinerarios-personales/
├── CLAUDE.md
├── README.md
├── .gitignore
├── .gitattributes
├── docker-compose.yml              ← Fase 10
├── .env.example
├── docs/
│   ├── 01-planificacion.md ... 06-decisiones-arquitectonicas.md
│   └── asyncapi/asyncapi.yaml      ← Fase 4
├── services/
│   ├── airport-service/
│   │   ├── app/
│   │   │   ├── domain/             ← Airport, Coordinates, excepciones
│   │   │   ├── application/        ← puertos y casos de uso
│   │   │   ├── infrastructure/
│   │   │   │   ├── api_colombia/   ← client, DTO externo, mapper, adapter
│   │   │   │   ├── cache/          ← Fase 2
│   │   │   │   └── resilience/     ← Fase 2
│   │   │   ├── api/                ← rutas, esquemas, errores, dependencias
│   │   │   ├── config.py
│   │   │   └── main.py
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   └── .env.example
│   └── itinerary-service/
│       ├── app/                    ← misma estructura hexagonal
│       │   └── infrastructure/
│       │       ├── persistence/
│       │       ├── airport_client/
│       │       └── messaging/
│       ├── alembic/
│       ├── alembic.ini
│       ├── tests/
│       └── requirements.txt
├── serverless/
│   ├── send-notification-function/
│   └── event-trigger/
├── gateway/
├── frontend/
│   ├── index.html
│   ├── css/
│   └── js/
├── observability/
│   ├── prometheus/
│   └── grafana/
└── tests/
    └── e2e/
```

Si necesitas cambiar esta estructura, explica el cambio y pide aprobación.

### 7.6. Puertos locales

| Componente | Puerto |
|---|---|
| API Gateway | 8000 |
| Airport Service | 8001 |
| Itinerary Service | 8002 |
| PostgreSQL (itinerarios) | 5433 |
| PostgreSQL (notificaciones) | 5434 (si se usa contenedor separado) |
| RabbitMQ | 5672 (AMQP) / 15672 (panel) |
| Redis | 6379 |
| SendNotificationFunction | 9000 |
| Jaeger | 16686 |
| Prometheus | 9090 |
| Grafana | 3000 |

---

## 8. Dominio (DDD)

### 8.1. Contextos delimitados

| Contexto | Servicio | Tipo | Relación |
|---|---|---|---|
| Catálogo de Aeropuertos | Airport Service | Soporte | Capa anticorrupción (Adapter) frente a API Colombia. Expone su API REST como lenguaje publicado |
| Planificación de Itinerarios | Itinerary Service | Principal (core) | Cliente del Catálogo vía REST |
| Notificaciones | Event Trigger + SendNotificationFunction | Genérico | Suscriptor del evento de integración. No conoce el modelo interno de itinerarios |

Entre contextos, las entidades se referencian **por identificador**: un itinerario guarda el
**ID** del aeropuerto, no el objeto `Airport`.

### 8.2. Lenguaje ubicuo

El **código se escribe en inglés** y la **documentación en español**.

| Término del negocio | Código | Significado |
|---|---|---|
| Aeropuerto | `Airport` | Lugar de salida o llegada según el catálogo |
| Código IATA / OACI | `iata_code` / `oaci_code` | Códigos internacionales (pueden faltar) |
| Coordenadas | `Coordinates` | Latitud y longitud ya validadas y corregidas |
| Itinerario | `Itinerary` | Plan de viaje entre dos aeropuertos |
| Viajero | `traveler_name` | Persona que viaja (el requisito dice "nombre del usuario") |
| Aeropuerto de salida | `departure_airport_id` | Referencia por ID al catálogo |
| Aeropuerto de llegada | `arrival_airport_id` | Referencia por ID al catálogo |
| Fecha de viaje | `travel_date` | Fecha (y hora, ver pendiente) de salida |
| Duración | `duration_minutes` | Duración estimada en minutos |
| Itinerario creado | `ItineraryCreatedEvent` | Hecho: se registró un nuevo itinerario |
| Mensaje pendiente | `OutboxMessage` | Evento guardado pendiente de publicar |
| Notificación | `NotificationRecord` | Registro de un aviso enviado |

Usa siempre estos nombres. No inventes sinónimos (`user`, `trip`, `origin`) en el código.

### 8.3. Entidades

**Airport** (solo lectura): `id`, `name`, `iata_code`, `oaci_code`, `type`, `city`, `department`,
`coordinates`. `iata_code`, `oaci_code` y `coordinates` pueden ser `None`.

Hallazgos de la verificación real de API Colombia (entrega 1A, 2026-10-26):

- `GET /Airport` devuelve 52 aeropuertos (ids 1 a 52). Campos externos: `id`, `name`, `iataCode`,
  `oaciCode`, `type`, `deparmentId` (sic, con error ortográfico), `department` (objeto con `name`),
  `cityId`, `city` (objeto con `name`), `latitude`, `longitude`.
- **Coordenadas intercambiadas** en 51 de 52: `latitude` trae la longitud (≈ −75) y `longitude` trae
  la latitud (≈ 4). El dominio no puede detectarlo por rangos: lo corrige el mapper (1B).
- El id 43 ("Aeropuerto del Café", en construcción) trae `0, 0`: ubicación desconocida.
- Los códigos faltantes llegan como el texto `"N/A"` (5 sin IATA, 3 sin OACI).
- Tipos observados: `Internacional`, `Nacional`, `Militar`, `En Construccion`.
- ID inexistente (9999) → 404 con cuerpo vacío. ID 0 o no numérico → 400 con cuerpo vacío.

**Coordinates** (objeto de valor): latitud entre −90 y 90, longitud entre −180 y 180.

**Itinerary** (raíz de agregado): `id` (UUID), `traveler_name`, `departure_airport_id`,
`arrival_airport_id`, `travel_date`, `duration_minutes`, `created_at`, `updated_at`.

**NotificationRecord**: `id`, `event_id` (único, para idempotencia), `itinerary_id`, `recipient`,
`channel` (`simulated-email`), `message`, `status` (`SENT` / `FAILED`), `processed_at`.

### 8.4. Reglas del dominio

Confirmadas por los requisitos:

- El itinerario incluye todos los datos obligatorios.
- Los aeropuertos de salida y llegada deben existir según Airport Service antes de guardar.
- La duración se expresa en minutos.
- La creación de un itinerario origina el evento correspondiente.
- "Aeropuerto no existe" (404) y "Airport Service no disponible" (503) se tratan de forma distinta.

Propuestas, **pendientes de confirmación** antes de la Fase 3:

- Salida distinta de llegada.
- Duración mayor que 0.
- La fecha de viaje no puede estar en el pasado al crear.
- El nombre del viajero no puede estar vacío.

---

## 9. Decisiones

### 9.1. Aceptadas

| Decisión | Detalle |
|---|---|
| Microservicios | Airport Service, Itinerary Service y sistema de notificaciones (ADR-001) |
| Arquitectura hexagonal | Dominio, casos de uso, puertos y adaptadores (ADR-002) |
| Adapter para API Colombia | Puerto interno + Adapter (ADR-003) |
| PostgreSQL para itinerarios | Propiedad exclusiva de Itinerary Service (ADR-004) |
| RabbitMQ | Mensajería de eventos de integración (ADR-005) |
| Transactional Outbox | Itinerario + evento en la misma transacción (ADR-006) |
| Redis | Caché en Airport Service (ADR-007) |
| Observabilidad | OpenTelemetry, Jaeger, Prometheus, Grafana, logs estructurados (ADR-010) |
| Entorno | Windows 11, PowerShell, Python 3.12 |
| Idioma | Código en inglés, documentación en español (ADR-011) |
| Formato de errores | Formato único de la sección 10.2 para todos los servicios (ADR-012) |
| Endpoints de Airport Service | Los de la sección 10.1 (ADR-012) |
| Puertos de Itinerary Service en el diagrama de componentes | Itinerary usa el puerto `AirportCatalog` + adaptador HTTP hacia el controlador REST de Airport, y el puerto `EventPublisher` en lugar de hablar directo con RabbitMQ (ADR-013) |
| Mensajes de commit | En español, con el prefijo de Conventional Commits en inglés (`feat: agrega ...`) |
| Uvicorn | Servidor ASGI para ejecutar FastAPI (agregado a `requirements.txt` en la entrega 1A) |
| Traducción de API Colombia (1B) | El mapper convierte `"N/A"` en `None` (códigos IATA/OACI) y deja `coordinates = None` cuando llegan `0, 0` |
| Corrección de coordenadas (1B) | No se invierten siempre: el mapper **detecta** el intercambio. Invierte solo si el valor de `latitude` está fuera del rango de latitudes de Colombia (aprox. −5 a 14) y el de `longitude` sí está dentro. Cada corrección registra un `warning` en el log. Pruebas obligatorias: coordenadas intercambiadas, correctas y `0, 0` |
| Tolerant Reader en la lista (1B) | En `list_airports`, un aeropuerto con formato inesperado o que viola el dominio se **omite** con un `warning` que lo identifica por su id (o por su posición si no tiene id); se devuelven los demás. Si la respuesta completa no es una lista o no es JSON válido → 502. En `get_airport_by_id`, un aeropuerto inválido → 502 |
| Pruebas asíncronas (1B) | Plugin de pytest de `anyio` (`@pytest.mark.anyio`), ya instalado como dependencia de httpx/FastAPI; no se agrega `pytest-asyncio` |
| Nombres externos (1B) | El campo `deparmentId` (con error ortográfico) solo existe en el DTO externo; el dominio usa nombres correctos |
| Validación del id (1C) | `GET /airports/{id}` valida que el id sea un entero mayor que 0 (422) antes de llamar a API Colombia. Un 404 de API Colombia se convierte en `AirportNotFoundError` (404) |

### 9.2. Propuestas (confirmar con el usuario antes de implementarlas)

| Decisión | Propuesta | Se necesita en |
|---|---|---|
| Endpoints de Itinerary Service | Ver sección 10.1 | Fase 3 |
| Contrato del evento | Ver sección 11 | Fase 4 |
| Topología RabbitMQ | Ver sección 11.2 | Fase 4 |
| Mejora del lenguaje ubicuo en `docs/03-dominio.md` | Separar términos del negocio de términos técnicos; agregar viajero, fecha de viaje, duración | Antes de la Fase 3 |
| Rama "Airport Service no disponible" en el diagrama de secuencia | Agregar respuesta 503 | Antes de la Fase 3 |
| Orden del flujo de resiliencia en `docs/05-diagramas.md` | Circuit breaker → llamada con timeout → retry con backoff → fallback. Un 404 no se reintenta ni activa fallback | Fase 2 |

### 9.3. Pendientes (no implementar sin decisión del usuario)

| Decisión | Opciones | Se necesita en |
|---|---|---|
| Base de datos: un servidor PostgreSQL con bases lógicas separadas, o un contenedor por servicio | Ambas cumplen "una base por servicio". `docs/` habla de "base de datos lógica" | Fase 3 |
| Tipo de `travel_date` | Solo fecha, o fecha y hora de salida (propuesta: fecha y hora con zona horaria) | Fase 3 |
| Campo opcional `traveler_email` | Para que la notificación simulada tenga destinatario | Fase 3 |
| Plataforma serverless (ADR-008) | Propuesta: imagen oficial de AWS Lambda para Python con el emulador de runtime (RIE), sin cuenta ni token. LocalStack requiere cuenta y auth token desde marzo de 2026. Knative y OpenFaaS requieren Kubernetes. Preguntar si el profesor exige una plataforma específica | Fase 6 |
| Almacenamiento del historial de notificaciones | Propuesta: PostgreSQL propio de notificaciones | Fase 6 |
| Gateway (ADR-009) | Propuesta: Nginx como gateway puro (enrutamiento, `limit_req`, reenvío del header `Authorization`) que también sirve el frontend en el mismo origen | Fase 7 |

Cuando una decisión se confirme, actualiza esta sección y `docs/06-decisiones-arquitectonicas.md`
(explicando el cambio antes de hacerlo).

---

## 10. Contratos HTTP

### 10.1. Endpoints previstos

Los endpoints de Airport Service están **aceptados**; los de Itinerary Service siguen como
propuesta hasta la Fase 3.

| Servicio | Método y ruta | Éxito | Errores |
|---|---|---|---|
| Airport | `GET /airports` | 200 | 502, 503 |
| Airport | `GET /airports/{id}` | 200 | 404, 422, 502, 503 |
| Airport | `GET /airports/map-data` | 200 (arrays para Plotly) | 502, 503 |
| Itinerary | `POST /itineraries` | 201 | 422, 503 |
| Itinerary | `GET /itineraries` | 200 | — |
| Itinerary | `GET /itineraries/{id}` | 200 | 404 |
| Itinerary | `PUT /itineraries/{id}` | 200 | 404, 422, 503 |
| Itinerary | `DELETE /itineraries/{id}` | 204 | 404 |
| Todos | `GET /health` | 200 | — |
| Todos | `GET /metrics` | 200 | — (Fase 9) |

En el Gateway: `/api/airports/...` → Airport Service y `/api/itineraries/...` → Itinerary Service.

El endpoint `map-data` tiene formato de presentación, así que vive en la capa `api`, no en el dominio.

### 10.2. Códigos de error (aceptado)

| Situación | Código |
|---|---|
| Recurso no encontrado | 404 |
| Validación de datos o aeropuerto inexistente al crear un itinerario | 422 |
| El proveedor externo respondió algo inesperado | 502 |
| Dependencia no disponible (API Colombia, Airport Service) | 503 |
| Timeout de una dependencia (Fase 2) | 504 |

Formato único de error para todos los servicios:

```json
{
  "error": {
    "code": "AIRPORT_NOT_FOUND",
    "message": "El aeropuerto con id 999 no existe",
    "details": {"field": "arrival_airport_id"}
  },
  "correlation_id": "3f2a..."
}
```

Los códigos de error (`code`) van en MAYÚSCULAS_CON_GUIONES_BAJOS y en inglés.

---

## 11. Eventos

### 11.1. Contrato de `ItineraryCreatedEvent` (versión 1, propuesta)

```json
{
  "event_id": "uuid",
  "event_type": "itinerary.created",
  "event_version": 1,
  "occurred_at": "2026-10-20T15:30:00Z",
  "producer": "itinerary-service",
  "correlation_id": "uuid",
  "data": {
    "itinerary_id": "uuid",
    "traveler_name": "Ana Pérez",
    "departure_airport_id": 1,
    "arrival_airport_id": 5,
    "travel_date": "2026-12-15T08:00:00-05:00",
    "duration_minutes": 75
  }
}
```

- Es un **evento de integración** (contrato público), distinto del evento de dominio interno.
- Cambios incompatibles requieren una nueva `event_version`.
- El contexto de trazas (`traceparent`) viaja en los headers AMQP (Fase 9).

### 11.2. Topología RabbitMQ (propuesta)

| Elemento | Nombre |
|---|---|
| Exchange | `itinerary.events` (topic, durable) |
| Routing key | `itinerary.created` |
| Cola | `notification.itinerary-created` (durable) |
| Dead letter exchange | `itinerary.events.dlx` |
| Cola de mensajes fallidos | `notification.itinerary-created.dlq` |

- Entrega **al menos una vez**: los consumidores deben ser **idempotentes** (clave: `event_id`).
- El consumidor confirma (ACK) solo después de completar el procesamiento.

---

## 12. Fases del proyecto

| Fase | Nombre | Contenido |
|---|---|---|
| 0 | Planificación y arquitectura | **Completada** (ver `docs/`) |
| 1 | Airport Service | FastAPI, hexagonal, dominio, puerto, Adapter, cliente API Colombia, traducción externo → interno, endpoints, errores, Swagger, Pydantic, tests básicos. **Sin Redis ni circuit breaker.** Demostrar: cliente → Airport Service → Adapter → API Colombia |
| 2 | Resiliencia y caché | Redis, caché, timeout, retry, exponential backoff, circuit breaker, fallback. Explicar cada mecanismo. Probar: API funciona, API tarda demasiado, API no responde, consultas repetidas |
| 3 | Itinerary Service | FastAPI, hexagonal, DDD básico, entidad Itinerary, PostgreSQL, SQLAlchemy, Pydantic, Alembic, CRUD completo, errores, Swagger. Validación HTTP de aeropuertos contra Airport Service antes de guardar |
| 4 | Eventos y RabbitMQ | `ItineraryCreatedEvent`, exchange, cola, routing key, contrato formal, AsyncAPI. Explicar: llamada HTTP vs evento vs evento de dominio vs evento de integración. Publicación directa tras el commit (para mostrar luego el problema de double write) |
| 5 | Transactional Outbox | Itinerario + evento en la misma transacción, worker/relay que publica en RabbitMQ. Explicar el problema de double write |
| 6 | Serverless | `SendNotificationFunction`: recibe el evento, simula la notificación, guarda historial, maneja errores. Explicar por qué es FaaS. Opcional: `GenerateItineraryReportFunction` |
| 7 | API Gateway | Punto único de entrada, enrutamiento, sin lógica de negocio, rate limiting básico, preparar propagación de JWT |
| 8 | Frontend | Consultar aeropuertos, mapa con Plotly JS, CRUD de itinerarios. Solo vía nuestros servicios |
| 9 | Observabilidad | Logs JSON, correlation ID, `trace_id`, `span_id`, OpenTelemetry, Jaeger, Prometheus, Grafana. Demostrar el recorrido completo Frontend → Gateway → Itinerary → Airport → BD → Evento → RabbitMQ → Función |
| 10 | Docker y Docker Compose | Contenedores para todos los componentes, `docker-compose.yml`, cómo levantar y detener todo |
| 11 | Pruebas | Unit, integración, API, Adapter, CRUD, comunicación HTTP, eventos, flujo completo. Opcional: E2E, Testcontainers |
| 12 | Documentación y entrega | README profesional con todos los diagramas (componentes, clases, relacional, secuencia, despliegue), instalación, ejecución, variables de entorno, endpoints, eventos, evidencias y pruebas |

### 12.1. Plan de la Fase 1 (entregas)

| Entrega | Contenido | Verificación |
|---|---|---|
| **1A** | Rama `fase-1-airport-service`, `.gitignore`, `.gitattributes`, carpeta `services/airport-service`. Verificar con consultas reales a API Colombia: campos, coordenadas (se reporta que latitud y longitud podrían venir intercambiadas), respuesta ante ID inexistente. Entorno virtual, `requirements.txt`, capa de dominio | Pruebas del dominio pasan |
| **1B** | Puerto `AirportProvider`, `ApiColombiaClient`, DTO externo, mapper, `ApiColombiaAirportAdapter` | Pruebas del Adapter con API simulada (respx) pasan |
| **1C** | Casos de uso, rutas REST, esquemas de respuesta, manejo de errores, inyección de dependencias, `main.py`, pruebas de API, demostración con datos reales | El servicio responde en `http://localhost:8001/docs` |

API Colombia: base `https://api-colombia.com/api/v1`, recursos `/Airport` y `/Airport/{id}`.
En la Fase 1 se usa el timeout por defecto de httpx; el timeout configurable se agrega en la Fase 2.

---

## 13. Estándares de código

- Type hints en todas las funciones.
- Pydantic v2 para esquemas de entrada y salida de la API y para el DTO externo.
- El dominio usa clases simples de Python (`dataclass` o similares), **no** modelos de FastAPI.
- Configuración con `pydantic-settings` leída de variables de entorno; cada servicio tiene un
  `.env.example` con todas las variables y valores de ejemplo.
- Las rutas FastAPI solo: reciben la solicitud, llaman al caso de uso y convierten el resultado
  o el error a HTTP.
- Las excepciones del dominio y de la aplicación se traducen a HTTP en un único manejador de errores.
- Nombres claros y en inglés; comentarios y docstrings breves en español cuando ayuden a explicar.
- Sin código muerto, sin `print` (usar `logging`). Logs básicos hasta la Fase 9, JSON desde la Fase 9.
- Sin sobreingeniería: si una abstracción no aporta a los requisitos, no se agrega.

## 14. Estándares de pruebas

- Framework: **pytest**.
- Las pruebas unitarias y del Adapter **no dependen de internet**: la API externa se simula con respx.
- Las pruebas de API usan el `TestClient` de FastAPI con proveedores falsos inyectados
  (`dependency_overrides`).
- Cada entrega incluye el comando exacto para correr sus pruebas, por ejemplo:

```powershell
cd services\airport-service
.\.venv\Scripts\Activate.ps1
pytest -v
```

- Ninguna entrega se considera terminada si sus pruebas fallan.

---

## 15. Estado actual

> Actualiza esta sección al terminar cada entrega o fase (explicando el cambio).

- **Fase 0:** completada (documentación en `docs/`).
- **Fase 1:** en curso en la rama `fase-1-airport-service`.
  - Entrega **1A** completada: `.gitignore`, `.gitattributes`, entorno y `requirements.txt` de
    Airport Service, capa de dominio (`Airport`, `Coordinates`, excepciones) con pruebas.
  - Entrega **1B** completada: puerto `AirportProvider`, excepciones de aplicación, `ApiColombiaClient`,
    DTO externo, mapper (corrección detectada de coordenadas, `"N/A"` → `None`, `0, 0` → sin ubicación)
    y `ApiColombiaAirportAdapter` (Tolerant Reader en la lista), con pruebas respx.
  - Siguiente: entrega **1C** cuando el usuario lo confirme.
- Diagrama de componentes de `docs/05-diagramas.md` corregido (ADR-013).
