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
| Terminal | **PowerShell** y **CMD** (no Bash) |
| Python | **3.12** (usar `py -3.12`) |
| Git | Git for Windows |
| Contenedores | Docker Desktop con WSL 2 (desde la Fase 2) |

### 4.1. Reglas para los comandos

- Todos los comandos se dan **para PowerShell y para CMD** de Windows 11 (los dos bloques, o uno solo
  si el comando es idéntico en ambas terminales y se indica así).
- PowerShell de Windows 11 es la versión **5.1**: no usar parámetros que solo existen en PowerShell 7
  (por ejemplo `-SkipHttpErrorCheck`). PowerShell 5.1 muestra mal las tildes de respuestas JSON sin
  `charset`; para demostraciones usar Swagger o `curl.exe`. En CMD, ejecutar `chcp 65001` antes de
  `curl.exe` para ver bien las tildes.
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

El flujo completo del equipo, para personas, está en [`CONTRIBUTING.md`](CONTRIBUTING.md).
Estas son las reglas que debes seguir tú:

- Repositorio: `https://github.com/JUANGR12192004/sistema-itinerarios-personales`
- Rama principal: `main`. **No se trabaja directamente sobre `main`.**
- Ramas desde `main` actualizado:
  - una rama por fase: `fase-1-airport-service`, `fase-2-resiliencia`, `fase-3-itinerary-service`, etc.;
  - una rama por tarea fuera de una fase: `tipo/descripcion-corta` (por ejemplo `chore/github-practices`).
- **Nunca hagas push forzado a `main` ni reescribas su historial** (`rebase`, `commit --amend`,
  `filter-branch` o similares sobre commits que ya están en `main`).
- **Ramas por fase de solo lectura:** la rama `fase-N-...` se **conserva** después del merge como
  archivo de la fase. No se trabaja en ella después de fusionarla: las correcciones salen siempre de
  una rama nueva desde `main` (por ejemplo `fix/...`). La versión integrada y vigente está en `main`.
- Las ramas auxiliares (`chore/`, `fix/`, `docs/`) **sí se borran** después del merge.
- **Coautoría:** ningún commit ni descripción de pull request lleva la línea
  `Co-Authored-By` de Claude (ni el pie "Generated with Claude Code"). Está desactivada en
  `.claude/settings.json` (`attribution.commit` y `attribution.pr` vacíos). Si aparece en un commit
  propio que todavía no se ha subido, quítala antes del push. Los commits de la Fase 3 la conservan
  porque son anteriores a esta regla y `main` no se vuelve a reescribir.
- Un commit por entrega (o varios separados por tipo), con mensajes en formato Conventional Commits:
  el prefijo en inglés y la descripción en español (por ejemplo `feat: agrega capa de dominio de Airport Service`):
  - `feat: ...` nueva funcionalidad
  - `fix: ...` corrección
  - `docs: ...` documentación
  - `test: ...` pruebas
  - `ci: ...` integración continua (GitHub Actions)
  - `chore: ...` configuración, dependencias, estructura
- Antes de hacer commit, muestra qué archivos cambiaron y propone el mensaje.
- Un issue por entrega (plantilla `.github/ISSUE_TEMPLATE/entrega.md`), con un milestone por fase.
  **Cuando una entrega tenga issue, el commit o el PR deben incluir `Closes #N`.**
- Los PR usan la plantilla `.github/pull_request_template.md`. Los PR los crea el equipo
  (pide confirmación antes de crear uno, sección 3.3).
- Antes del merge: la integración continua (`.github/workflows/tests.yml`, check "Pruebas") debe
  pasar y debe haber **1 aprobación de otro integrante** (acuerdo del equipo; `main` aún no tiene
  protección en GitHub). Quien revisa aprueba y quien hizo el PR fusiona, con
  **"Create a merge commit"**. Después se borra la rama solo si es auxiliar (`chore/`, `fix/`,
  `docs/`); la rama `fase-N-...` se conserva como archivo de solo lectura.
- **Nunca intentes aprobar ni fusionar pull requests**, aunque tengas acceso para hacerlo.
- La integración a `main` se hace cuando la lista de verificación de la fase está completa.
- **Al terminar cada fase, después del merge, se crea la etiqueta anotada `fase-N`** sobre el
  commit del merge (`git tag -a fase-N -m "..."` y `git push origin fase-N`). Tú la propones y
  esperas confirmación antes de crearla y subirla.
- Las fases rotan entre los tres integrantes; el responsable de cada fase figura en su milestone.
- El correo de los commits se configura solo para este repositorio (`git config user.email`, sin
  `--global`). No cambies la configuración de Git del equipo.
- Cuando agregues un servicio con pruebas, agrega su job en `.github/workflows/tests.yml`.

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
| Mensajería | RabbitMQ (cliente `pika`, ADR-021) |
| Caché | Redis |
| Frontend | HTML, CSS, JavaScript, Plotly JS |
| Contenedores | Docker y Docker Compose |
| Serverless | Ver decisión pendiente en la sección 9 |
| Observabilidad | OpenTelemetry, Jaeger, Prometheus, Grafana |
| Documentación | Swagger / OpenAPI, AsyncAPI |
| Pruebas | pytest, TestClient de FastAPI, respx (simular HTTP externo) |
| Calidad de código | SonarCloud con **Automatic Analysis** (lo conectó el equipo desde SonarCloud con su GitHub App; no hay paso en GitHub Actions). Se configura con `.sonarcloud.properties` en la raíz: Python 3.12, `services` como fuente (sin `tests` ni migraciones de Alembic) y las carpetas `tests` como código de pruebas (ADR-023) |

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
├── CONTRIBUTING.md                 ← flujo de trabajo del equipo
├── .github/
│   ├── pull_request_template.md
│   ├── ISSUE_TEMPLATE/entrega.md
│   └── workflows/tests.yml         ← integración continua (un job por servicio)
├── .gitignore
├── .gitattributes
├── .sonarcloud.properties          ← configuración de SonarCloud (Automatic Analysis)
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
| Correo del viajero | `traveler_email` | Correo electrónico opcional; lo usa la notificación simulada de la Fase 6 |
| Aeropuerto de salida | `departure_airport_id` | Referencia por ID al catálogo |
| Aeropuerto de llegada | `arrival_airport_id` | Referencia por ID al catálogo |
| Fecha de viaje | `travel_date` | Fecha y hora de salida con zona horaria (ADR-017) |
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

**Itinerary** (raíz de agregado): `id` (UUID), `traveler_name`, `traveler_email` (opcional), `departure_airport_id`,
`arrival_airport_id`, `travel_date` (con zona horaria), `duration_minutes`, `created_at`, `updated_at`.

**NotificationRecord**: `id`, `event_id` (único, para idempotencia), `itinerary_id`, `recipient`,
`channel` (`simulated-email`), `message`, `status` (`SENT` / `FAILED`), `processed_at`.

### 8.4. Reglas del dominio

Confirmadas por los requisitos:

- El itinerario incluye todos los datos obligatorios.
- Los aeropuertos de salida y llegada deben existir según Airport Service antes de guardar.
- La duración se expresa en minutos.
- La creación de un itinerario origina el evento correspondiente.
- "Aeropuerto no existe" (404) y "Airport Service no disponible" (503) se tratan de forma distinta.

Confirmadas en la Fase 3 (ADR-015):

- El nombre del viajero no puede estar vacío.
- Salida distinta de llegada.
- Duración mayor que 0.
- La fecha de viaje no puede estar en el pasado al crear; debe incluir zona horaria (ADR-017).

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
| Corrección de coordenadas (1B) | No se invierten siempre: el mapper **detecta** el intercambio. Invierte solo si el valor de `latitude` está fuera del rango de latitudes de Colombia (aprox. −5 a 14) y el de `longitude` sí está dentro. El mapper registra cada corrección en `DEBUG` y el Adapter registra **un solo `WARNING` por respuesta** con el total de aeropuertos corregidos (por ejemplo "51 de 52"). Pruebas obligatorias: coordenadas intercambiadas, correctas y `0, 0` |
| Tolerant Reader en la lista (1B) | En `list_airports`, un aeropuerto con formato inesperado o que viola el dominio se **omite** con un `warning` que lo identifica por su id (o por su posición si no tiene id); se devuelven los demás. Si la respuesta completa no es una lista o no es JSON válido → 502. Si la lista no está vacía pero **todos** sus aeropuertos son inválidos → 502 (indica un cambio de contrato del proveedor); una lista vacía `[]` se devuelve vacía. En `get_airport_by_id`, un aeropuerto inválido → 502 |
| Pruebas asíncronas (1B) | Plugin de pytest de `anyio` (`@pytest.mark.anyio`), ya instalado como dependencia de httpx/FastAPI; no se agrega `pytest-asyncio` |
| Nombres externos (1B) | El campo `deparmentId` (con error ortográfico) solo existe en el DTO externo; el dominio usa nombres correctos |
| Validación del id (1C) | `GET /airports/{id}` valida que el id sea un entero mayor que 0 (422) antes de llamar a API Colombia. Un 404 de API Colombia se convierte en `AirportNotFoundError` (404) |
| Orden del flujo de resiliencia (Fase 2, ADR-014) | Caché → circuit breaker → retry con exponential backoff → llamada con timeout → fallback. El circuit breaker envuelve al retry (una consulta = un fallo para el circuito). Un 404 no se reintenta, no se cachea, no abre el circuito ni activa el fallback. Un 502 tampoco se reintenta ni activa el fallback |
| Mecanismos de resiliencia (Fase 2, ADR-014) | Implementados a mano en `infrastructure/resilience` (sin `tenacity` ni `pybreaker`), como el Decorator `ResilientAirportProvider`. Valores por defecto: timeout 3 s, 3 intentos, backoff 0.5 s → 1 s (máx. 4 s), circuito abierto tras 3 fallos seguidos durante 30 s. Timeout agotado → 504 `AIRPORT_PROVIDER_TIMEOUT` (`AirportProviderTimeoutError`, subclase de `AirportProviderUnavailableError`); circuito abierto → 503 |
| Caché y fallback (Fase 2, ADR-007) | Librería `redis==8.1.0` (`redis.asyncio`). Decorator `CachedAirportProvider` sobre la interfaz `CacheStore` (`RedisCacheStore`; almacén en memoria en las pruebas, sin `fakeredis`). Copia fresca 10 min y de respaldo 24 h, que se usa como fallback solo si el proveedor no está disponible. Header `X-Cache`: `HIT`, `MISS` o `STALE`. Si Redis falla, el servicio sigue sin caché y no lo reintenta durante 30 s |
| Redis local (Fase 2) | Hasta la Fase 10 se ejecuta con `docker run -d --name airport-redis -p 6379:6379 redis:7.4-alpine` |
| Reglas de negocio de Itinerary Service (Fase 3, ADR-015) | Nombre no vacío, salida distinta de llegada, duración mayor que 0, fecha de viaje no puede estar en el pasado al crear |
| PostgreSQL por contenedor (Fase 3, ADR-016) | Un contenedor por servicio; `itinerary-postgres` (postgres:16-alpine) en el puerto 5433, usuario/clave `itinerary`, base `itinerary_db` |
| `travel_date` con zona horaria (Fase 3, ADR-017) | Fecha y hora con zona horaria (`datetime` con `tzinfo`), coherente con el contrato del evento |
| `traveler_email` opcional (Fase 3, ADR-018) | Campo opcional en `Itinerary`; lo usa la notificación simulada de la Fase 6 |
| Endpoints de Itinerary Service (Fase 3, ADR-019) | Los de la sección 10.1; un timeout de Airport Service → 504 en Itinerary Service (extiende ADR-012) |
| Contrato de `ItineraryCreatedEvent` v1 (Fase 4, ADR-020) | El de la sección 11.1, con `data.traveler_email` (texto o `null`). El evento vive en la capa de aplicación (`app/application/events.py`) |
| Topología RabbitMQ y librería (Fase 4, ADR-021) | La de la sección 11.2, con `pika==1.3.2` (síncrono, una conexión por publicación), mensajes persistentes, publisher confirms y `mandatory=True`. Hasta la Fase 6 el publicador declara toda la topología |
| Publicación directa tras el commit (Fase 4, ADR-022) | Puerto `UnitOfWork`; el caso de uso hace guardar → commit → publicar. Si RabbitMQ falla tras el commit: 201 + log `ERROR` "Evento perdido" (double write, lo resuelve la Fase 5) |
| SonarCloud (PR #7, ADR-023) | Análisis de calidad con **Automatic Analysis** (sin paso en GitHub Actions), configurado en `.sonarcloud.properties`. No importa cobertura. Su Quality Gate no forma parte por ahora del acuerdo de merge (check "Pruebas" + 1 aprobación) |

### 9.2. Propuestas (confirmar con el usuario antes de implementarlas)

Ninguna por ahora (el contrato del evento y la topología de RabbitMQ se aceptaron en la Fase 4:
ADR-020 y ADR-021).

### 9.3. Pendientes (no implementar sin decisión del usuario)

| Decisión | Opciones | Se necesita en |
|---|---|---|
| Plataforma serverless (ADR-008) | Propuesta: imagen oficial de AWS Lambda para Python con el emulador de runtime (RIE), sin cuenta ni token. LocalStack requiere cuenta y auth token desde marzo de 2026. Knative y OpenFaaS requieren Kubernetes. Preguntar si el profesor exige una plataforma específica | Fase 6 |
| Almacenamiento del historial de notificaciones | Propuesta: PostgreSQL propio de notificaciones | Fase 6 |
| Gateway (ADR-009) | Propuesta: Nginx como gateway puro (enrutamiento, `limit_req`, reenvío del header `Authorization`) que también sirve el frontend en el mismo origen | Fase 7 |
| Protección de `main` y de las ramas `fase-*` | Se configura en GitHub (*Settings → Rules → Rulesets* o *Branches*). Propuesta: en `main`, exigir PR con 1 aprobación y el check "Pruebas", y bloquear push forzado y borrado; en `fase-*`, bloquear push, push forzado y borrado (solo lectura). Hoy son solo acuerdos del equipo. Lo decide y configura el dueño del repositorio | Antes de la Fase 5 o cuando el equipo lo decida |
| Advertencia de Starlette en las pruebas | `pytest` muestra `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead` (detectada en la entrega 1C). Por ahora **no se oculta ni se instala `httpx2`**. Opciones: migrar a `httpx2`, fijar versiones que no la emitan, o filtrarla documentando el motivo | Fase 11 |

Cuando una decisión se confirme, actualiza esta sección y `docs/06-decisiones-arquitectonicas.md`
(explicando el cambio antes de hacerlo).

---

## 10. Contratos HTTP

### 10.1. Endpoints previstos

Los endpoints de Airport Service y de Itinerary Service están **aceptados** (ADR-012, ADR-019).

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

### 11.1. Contrato de `ItineraryCreatedEvent` (versión 1, aceptado, ADR-020)

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
    "traveler_email": "ana@example.com",
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

### 11.2. Topología RabbitMQ (aceptada, ADR-021)

| Elemento | Nombre |
|---|---|
| Exchange | `itinerary.events` (topic, durable) |
| Routing key | `itinerary.created` |
| Cola | `notification.itinerary-created` (durable) |
| Dead letter exchange | `itinerary.events.dlx` (direct, durable) |
| Cola de mensajes fallidos | `notification.itinerary-created.dlq` (durable) |

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

### 12.2. Plan de la Fase 2 (entregas)

Por decisión del usuario, las tres entregas se hicieron seguidas en la rama `fase-2-resiliencia`,
con una sola pausa al final de la fase.

| Entrega | Contenido | Verificación |
|---|---|---|
| **2A** | Timeout configurable, `AirportProviderTimeoutError` (504), `RetryPolicy` con exponential backoff | Pruebas de cliente y retry |
| **2B** | `CircuitBreaker` (CLOSED/OPEN/HALF_OPEN), `ResilientAirportProvider`, fallback con la copia de respaldo | Pruebas del circuit breaker y del proveedor resiliente |
| **2C** | Redis: `CacheStore`, `RedisCacheStore`, `CachedAirportProvider`, header `X-Cache`, ensamblaje en `main.py`, escenarios (funciona, tarda, no responde, consultas repetidas) | `pytest -v tests\integration` y demostración del README del servicio |

### 12.3. Plan de la Fase 3 (entregas)

| Entrega | Contenido | Verificación |
|---|---|---|
| **3A** | Carpeta `services/itinerary-service`, `requirements.txt`, `.env.example`, `config.py`, capa de dominio (`Itinerary`, reglas de negocio, excepciones) con pruebas | Pruebas del dominio pasan (`pytest -v tests/domain`) |
| **3B** | Puertos (`ItineraryRepository`, `AirportCatalog`, `EventPublisher` solo definido), `SqlAlchemyItineraryRepository`, modelo ORM, Alembic con la primera migración aplicada a PostgreSQL | Migración aplicada; `alembic current` muestra la revisión activa |
| **3C** | `HttpAirportCatalogAdapter` (llama a `GET /airports/{id}` de Airport Service con timeout; 404 → 422, 503/504 → propaga el código) con pruebas respx | Pruebas del adaptador pasan sin internet |
| **3D** | Casos de uso CRUD, rutas, esquemas Pydantic, manejador único de errores, correlation ID, `main.py` en el puerto 8002, Swagger, pruebas de API, job de CI en `tests.yml`, README, demostración real Itinerary → Airport → API Colombia | El servicio responde en `http://localhost:8002/docs` |

### 12.4. Plan de la Fase 4 (entregas)

Rama `fase-4-eventos-rabbitmq`. Una pausa al final de cada entrega (decisión del usuario).

| Entrega | Contenido | Verificación |
|---|---|---|
| **4A** | ADR-020 a ADR-022, evento de integración `ItineraryCreatedEvent`, `EventPublishError`, puerto `UnitOfWork` y `SqlAlchemyUnitOfWork`, puerto `EventPublisher.publish(event)`, caso de uso guardar → commit → publicar, correlation ID en el evento, fakes y pruebas | `pytest -v tests\application tests\api` pasa |
| **4B** | `pika`, configuración de RabbitMQ, declaración de la topología, `RabbitMQEventPublisher` (persistente, confirms, `mandatory`), ensamblaje en `dependencies.py`, pruebas unitarias con canal falso e integración con RabbitMQ real (SKIPPED sin RabbitMQ) | Pruebas del publicador pasan sin RabbitMQ |
| **4C** | `docs/asyncapi/asyncapi.yaml`, explicación HTTP vs evento vs evento de dominio vs evento de integración, diagramas, README del servicio con la demostración (RabbitMQ en Docker, panel 15672, double write), estado de CLAUDE.md, PR | Mensaje visible en la cola `notification.itinerary-created` |

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
- **Historial de `main`:** se reescribió una vez con un push forzado (intento de quitar la línea de
  coautoría de Claude de los commits de la Fase 3, que todavía la tienen). Los identificadores de esta
  sección son los actuales de `main`. No se vuelve a reescribir `main` (sección 5).
- **Fase 1:** completada y **fusionada en `main`** (PR #2, merge `fad95fe`) con la **etiqueta `fase-1`**
  (97 pruebas). Documentación del servicio en `services/airport-service/README.md`.
  - Entrega **1A** completada: `.gitignore`, `.gitattributes`, entorno y `requirements.txt` de
    Airport Service, capa de dominio (`Airport`, `Coordinates`, excepciones) con pruebas.
  - Entrega **1B** completada: puerto `AirportProvider`, excepciones de aplicación, `ApiColombiaClient`,
    DTO externo, mapper (corrección detectada de coordenadas, `"N/A"` → `None`, `0, 0` → sin ubicación)
    y `ApiColombiaAirportAdapter` (Tolerant Reader en la lista), con pruebas respx.
  - Entrega **1C** completada: casos de uso, rutas REST,
    esquemas, manejador único de errores (`AIRPORT_NOT_FOUND`, `VALIDATION_ERROR`,
    `AIRPORT_PROVIDER_BAD_RESPONSE`, `AIRPORT_PROVIDER_UNAVAILABLE`, `ROUTE_NOT_FOUND`, `METHOD_NOT_ALLOWED`,
    `INTERNAL_ERROR`),
    correlation ID por header `X-Correlation-ID`, inyección de dependencias, `main.py`, logging de `app.*`
    en consola y pruebas de API con proveedor falso.
- Diagrama de componentes de `docs/05-diagramas.md` corregido (ADR-013).
- Buenas prácticas del repositorio (rama `chore/github-practices`): plantillas de PR e issue,
  integración continua con GitHub Actions y `CONTRIBUTING.md`.
- **Fase 2:** completada y **fusionada en `main`** (PR #4, merge `d02b2ff`). Etiqueta `fase-2` creada. Timeout configurable (504), retry con exponential backoff, circuit breaker, caché en Redis como Decorator con fallback de datos de respaldo y header `X-Cache` (ADR-007 y ADR-014).
- **Fase 3:** completada y **fusionada en `main`** (PR #6, merge `b145360`) con la **etiqueta `fase-3`**.
  - Entrega **3A** completada: carpeta `services/itinerary-service`, `requirements.txt`, `.env.example`, `pytest.ini`, `config.py`, capa de dominio (`Itinerary`, `InvalidItineraryError`, `DomainError`) con 16 pruebas.
  - Entrega **3B** completada: puertos (`ItineraryRepository`, `AirportCatalog`, `EventPublisher`), `SqlAlchemyItineraryRepository`, modelo ORM `ItineraryORM`, `database.py`, Alembic (migración `a3f1e2b4c5d0` aplicada), `FakeItineraryRepository` con 13 pruebas, pruebas de integración contra PostgreSQL real en `tests/integration/` (8 pruebas, SKIPPED en CI).
  - Entrega **3C** completada: `HttpAirportCatalogAdapter` (404→`AirportNotFoundInCatalogError`, 504/timeout→`AirportServiceTimeoutError`, 503/502/red→`AirportServiceUnavailableError`) con 7 pruebas respx.
  - Entrega **3D** completada: casos de uso CRUD (`CreateItineraryUseCase`, `GetItineraryUseCase`, `ListItinerariesUseCase`, `UpdateItineraryUseCase`, `DeleteItineraryUseCase`), `NoopEventPublisher`, esquemas Pydantic, manejador único de errores (7 tipos), `dependencies.py` (Unit of Work con SQLAlchemy), rutas FastAPI en `/itineraries`, `main.py` en el puerto 8002, `README.md`, job de CI en `tests.yml`. 16 pruebas de API con fakes. Total del servicio: **52 pruebas pasan, 8 omitidas** (integración sin PostgreSQL en CI).
- SonarCloud agregado (PR #7, merge `dac1acc`, ADR-023).
- **Fase 4:** completada y **fusionada en `main`** (PR #8, merge `bbeebd3`) con la **etiqueta `fase-4`**.
  La rama `fase-4-eventos-rabbitmq` se conserva como archivo de solo lectura.
  - Entrega **4A** completada: decisiones ADR-020 a ADR-022, `ItineraryCreatedEvent` (capa de aplicación),
    `EventPublishError`, puerto `UnitOfWork` con `SqlAlchemyUnitOfWork`, `EventPublisher.publish(event)`,
    `CreateItineraryUseCase` con guardar → commit → publicar (201 + log `ERROR` si falla la publicación),
    correlation ID de `X-Correlation-ID` en el evento. Total del servicio: **75 pruebas pasan, 9 omitidas**.
  - Entrega **4B** completada: `pika==1.3.2`, variables `RABBITMQ_URL` y `RABBITMQ_TIMEOUT_SECONDS`,
    `topology.py` (exchange, cola, DLX y DLQ durables), `RabbitMQEventPublisher` (una conexión por publicación,
    confirms, `mandatory=True`, mensajes persistentes, `message_id = event_id`, errores → `EventPublishError`),
    ensamblado en `dependencies.py`. Se elimina `NoopEventPublisher` (ya sin uso). 13 pruebas con canal falso y
    1 de integración con RabbitMQ real (SKIPPED sin RabbitMQ). Total: **88 pruebas pasan, 10 omitidas**.
  - Entrega **4C** completada: `docs/asyncapi/asyncapi.yaml` (AsyncAPI 3.0) con 5 pruebas que lo comparan
    con el evento del código, `docs/04-comunicacion-y-eventos.md` (contrato, topología, HTTP vs evento vs evento de
    dominio vs evento de integración, double write), diagrama de secuencia de `docs/05-diagramas.md` y README del
    servicio con la demostración (RabbitMQ en Docker, mensaje en la cola, double write).
    Total del servicio: **93 pruebas pasan, 10 omitidas**.
- **Cierre de la Fase 4** (rama `chore/cierre-fase-4`): `.claude/settings.json` sin coautoría de Claude,
  reglas de coautoría, de no reescribir `main` y de ramas por fase de solo lectura (sección 5,
  `CONTRIBUTING.md` y `README.md`), ADR-023 de SonarCloud, y en Itinerary Service: pruebas sin `.env`
  (`tests/conftest.py`), `connect_timeout` de 2 s en el fixture `pg_engine` (de 4,5 min a ~12 s sin
  PostgreSQL en Windows) y variable `DATABASE_CONNECT_TIMEOUT_SECONDS` (por defecto 5) en el engine.
  Total de Itinerary Service: **100 pruebas pasan, 10 omitidas**.
- **Siguiente:** Fase 5 — Transactional Outbox (no iniciada).
