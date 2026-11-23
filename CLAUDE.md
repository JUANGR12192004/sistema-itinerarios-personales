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

El equipo tiene **tres integrantes**. Trabajan en **Windows 11** y en **macOS (Apple Silicon)**.

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
8. Comandos exactos para instalar dependencias (PowerShell, CMD y zsh, sección 4).
9. Comandos exactos para ejecutar (PowerShell, CMD y zsh, sección 4).
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

## 4. Entorno de desarrollo (Windows 11 y macOS)

| Herramienta | Versión / detalle |
|---|---|
| Sistema operativo | Windows 11 y macOS con Apple Silicon (el equipo usa los dos) |
| Terminal | **PowerShell** y **CMD** en Windows; **Terminal de macOS (zsh)** en macOS |
| Python | **3.12** (`py -3.12` en Windows, `python3.12` en macOS) |
| Git | Git for Windows / Git de macOS (Xcode Command Line Tools o Homebrew) |
| Contenedores | Docker Desktop (con WSL 2 en Windows; versión para Apple Silicon en macOS) |

### 4.1. Reglas para los comandos

- Todos los comandos se dan **para PowerShell, CMD y la Terminal de macOS (zsh)**: un bloque por terminal,
  o uno solo si el comando es idéntico en todas, indicándolo (por ejemplo, los comandos `docker`, `git`,
  `alembic`, `pytest` y `python -m ...` con el entorno virtual activado).
- PowerShell de Windows 11 es la versión **5.1**: no usar parámetros que solo existen en PowerShell 7
  (por ejemplo `-SkipHttpErrorCheck`). PowerShell 5.1 muestra mal las tildes de respuestas JSON sin
  `charset`; para demostraciones usar Swagger o `curl.exe`. En CMD, ejecutar `chcp 65001` antes de
  `curl.exe` para ver bien las tildes. En macOS no hace falta: la Terminal ya usa UTF-8.
- Usa rutas de Windows (`.\carpeta\archivo`) en los bloques de PowerShell y CMD, y rutas con `/` en los de zsh.
- El proyecto vive en `$HOME\proyectos\sistema-itinerarios-personales` (Windows) o
  `~/proyectos/sistema-itinerarios-personales` (macOS). Nunca trabajes en `C:\WINDOWS\system32` ni pidas
  ejecutar PowerShell como administrador (o `sudo` en macOS) salvo que sea indispensable (y explica por qué).
- Para llamadas HTTP de prueba usa `Invoke-RestMethod` o `curl.exe` en Windows (con `.exe`, porque en
  PowerShell `curl` puede ser un alias de `Invoke-WebRequest`) y `curl` en macOS.
- Cada servicio Python tiene su propio entorno virtual en `services/<servicio>/.venv`.
- En Apple Silicon las imágenes Docker del proyecto (PostgreSQL, RabbitMQ, Redis y la base de AWS Lambda)
  se descargan y construyen para `arm64` de forma nativa; no hace falta `--platform`.

### 4.2. Equivalencias entre terminales

| Acción | PowerShell | CMD | macOS (zsh) |
|---|---|---|---|
| Ruta de una carpeta | `services\itinerary-service` | `services\itinerary-service` | `services/itinerary-service` |
| Subir dos niveles | `cd ..\..` | `cd ..\..` | `cd ../..` |
| Crear el entorno virtual | `py -3.12 -m venv .venv` | `py -3.12 -m venv .venv` | `python3.12 -m venv .venv` |
| Activar el entorno virtual | `.\.venv\Scripts\Activate.ps1` | `.venv\Scripts\activate.bat` | `source .venv/bin/activate` |
| Permitir activar entornos (una vez) | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` | No aplica | No aplica |
| Copiar un archivo | `Copy-Item .env.example .env` | `copy .env.example .env` | `cp .env.example .env` |
| Asignar una variable de entorno | `$env:NOMBRE = "valor"` | `set NOMBRE=valor` | `export NOMBRE=valor` |
| Quitar una variable de entorno | `Remove-Item Env:NOMBRE` | `set NOMBRE=` | `unset NOMBRE` |
| Cliente HTTP | `curl.exe` o `Invoke-RestMethod` | `curl.exe` | `curl` |
| Enviar un archivo con curl | `--data-binary "@demo\archivo.json"` | `--data-binary "@demo\archivo.json"` | `--data-binary "@demo/archivo.json"` |
| Descartar la salida de curl | `-o NUL` | `-o NUL` | `-o /dev/null` |
| JSON en la línea de comandos | `-d '{\"clave\":1}'` | `-d "{\"clave\":1}"` | `-d '{"clave":1}'` |
| Continuar un comando en otra línea | `` ` `` al final | `^` al final | `\` al final |
| Ver bien las tildes | Swagger o `curl.exe` | `chcp 65001` | No hace falta |
| Detener un proceso | Ctrl+C | Ctrl+C | Ctrl+C |

### 4.3. Entorno virtual (por servicio)

**PowerShell:**

```powershell
# Solo una vez por equipo, para permitir activar entornos virtuales:
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# Dentro de la carpeta del servicio:
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**CMD:**

```cmd
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**macOS (zsh):**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4.4. Finales de línea

Windows usa CRLF; macOS y los contenedores Linux usan LF. El repositorio debe tener un `.gitattributes`
que normalice a LF los archivos de texto (en especial scripts `.sh`, `Dockerfile` y `.py`). En macOS no hay
conversión: los archivos se guardan con LF, igual que en el repositorio.

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
| API Gateway | Nginx, imagen oficial `nginx:1.30.6-alpine-otel` (ADR-009, ADR-036) |
| Frontend | HTML, CSS, JavaScript, Plotly JS. Fuente D-DIN (SIL OFL 1.1) local en `frontend/fonts/`: recurso estático, no librería |
| Contenedores | Docker y Docker Compose |
| Serverless | Imagen oficial de AWS Lambda `public.ecr.aws/lambda/python:3.12` con el Runtime Interface Emulator (ADR-008) |
| Observabilidad | `python-json-logger==4.2.0` (logs JSON), `opentelemetry-sdk==1.45.2` + instrumentadores (trazas), `prometheus-client==0.21.1` (métricas), Jaeger 2.23.0, Grafana 11.3.1 |
| Paquete compartido | `libs/observability` — Microservice Chassis Pattern: logging, trazas y métricas HTTP comunes a los cuatro componentes Python (ADR-040) |
| Documentación | Swagger / OpenAPI, AsyncAPI |
| Evidencias (herramienta de desarrollo) | `playwright==1.64.1` con Chromium, solo en `scripts/requirements-evidencias.txt` y el entorno `scripts/.venv`; no es dependencia de ningún servicio (Fase 12) |
| Pruebas | pytest, TestClient de FastAPI, respx (simular HTTP externo), `pyyaml==6.0.3` (dependencia directa solo en `requirements-dev.txt` de SendNotificationFunction, para leer el AsyncAPI en su prueba de contrato; Fase 11) |
| Calidad de código | SonarCloud con **Automatic Analysis** (lo conectó el equipo desde SonarCloud con su GitHub App; no hay paso en GitHub Actions). Se configura con `.sonarcloud.properties` en la raíz: Python 3.12, `services`, `serverless` y `libs` como fuente (sin `tests` ni migraciones de Alembic) y las carpetas `tests` como código de pruebas (ADR-023, ADR-040) |

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

| Puerto | Implementación |
|---|---|
| `ItineraryRepository` | `SqlAlchemyItineraryRepository` |
| `AirportCatalog` | `HttpAirportCatalogAdapter` (llama a `GET /airports/{id}` de Airport Service) |
| `EventPublisher` | Fase 4: `RabbitMQEventPublisher` (desde la Fase 5 lo usa solo el Outbox Relay). Fase 5: `OutboxEventPublisher` (mismo puerto; el caso de uso sigue sin conocer RabbitMQ ni la outbox, pero **cambia el orden**: registra el evento **antes** del commit, dentro de la misma transacción) |

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
├── docker-compose.e2e.yml          ← Fase 11: simulador de API Colombia para las pruebas E2E
├── .env.example
├── docs/
│   ├── 01-planificacion.md ... 06-decisiones-arquitectonicas.md
│   ├── 07-ejecucion-manual.md      ← Fase 12: arranque manual (modo desarrollo)
│   ├── 08-demostraciones.md        ← Fase 12: demostraciones de punta a punta y de observabilidad
│   ├── 09-guia-sustentacion.md     ← Fase 12: preparación, guion, reparto y preguntas probables
│   ├── 10-historial-de-fases.md    ← Fase 12: resumen de lo que aportó cada fase
│   ├── evidencias/                 ← Fase 12: README.md (índice) y las evidencias 01 a 21 (.txt y .png)
│   ├── asyncapi/asyncapi.yaml      ← Fase 4
│   └── openapi/airport-service.json ← Fase 11: contrato HTTP publicado de Airport Service
├── libs/
│   └── observability/              ← Fase 9: Microservice Chassis Pattern (ADR-040)
│       ├── pyproject.toml          ← paquete instalable con pip install -e
│       └── observability/
│           ├── __init__.py
│           ├── logging_config.py   ← configure_logging, set_correlation_id, filtros JSON
│           ├── tracing.py          ← setup_tracing(service_name, instrumentors, batch)
│           └── metrics.py          ← metrics_middleware, metrics_app, HTTP_REQUESTS, HTTP_DURATION
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
│   ├── send-notification-function/ ← Fase 6: app/ hexagonal, handler.py, alembic/, events/, Dockerfile
│   └── event-trigger/              ← Fase 6: app/ (application, infrastructure), main.py, replay_dlq.py, demo/
├── gateway/                        ← Fase 7: nginx.conf, Dockerfile (Nginx), templates/default.conf.template, tests/
├── frontend/
│   ├── index.html
│   ├── css/
│   ├── js/
│   └── fonts/                      ← D-DIN (.woff2) con OFL-1.1.txt y FONTLOG.txt (mejora del frontend)
├── observability/
│   ├── prometheus/
│   └── grafana/
├── scripts/
│   ├── lock_requirements.py        ← genera y comprueba (--check) los requirements-lock.txt de las imágenes
│   ├── evidencias_terminal.py      ← Fase 12: evidencias de terminal (librería estándar)
│   ├── capturar_evidencias.py      ← Fase 12: capturas web con Playwright
│   └── requirements-evidencias.txt ← Fase 12: Playwright, en su propio entorno scripts/.venv
└── tests/
    └── e2e/                        ← Fase 11: pruebas de punta a punta (pytest + httpx) y api_colombia_stub/
```

Si necesitas cambiar esta estructura, explica el cambio y pide aprobación.

### 7.6. Puertos locales

| Componente | Puerto |
|---|---|
| API Gateway | 8000 |
| Airport Service | 8001 |
| Itinerary Service | 8002 |
| PostgreSQL (itinerarios) | 5433 |
| PostgreSQL (notificaciones) | 5434 (contenedor `notification-postgres`, ADR-029) |
| RabbitMQ | 5672 (AMQP) / 15672 (panel) |
| Redis | 6379 |
| SendNotificationFunction | 9000 |
| Outbox Relay (métricas) | 9101 (proceso aparte de Itinerary Service, ADR-038) |
| Event Trigger (métricas) | 9102 (proceso aparte, ADR-038) |
| Jaeger (interfaz) | 16686 |
| Jaeger (recepción de trazas OTLP gRPC) | 4317 |
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

**NotificationRecord** (tabla `notification_history`, ADR-029 y ADR-030): `id`, `event_id` (único, para
idempotencia), `itinerary_id`, `recipient` (`None` si no hay correo), `channel` (`simulated-email`), `message`,
`status` (`SENT` / `SKIPPED`; `SKIPPED` reemplaza a `FAILED` desde la Fase 6), `status_reason` (por qué no se
envió), `correlation_id`, `processed_at`.

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
| Entorno | Windows 11 (PowerShell y CMD) y macOS con Apple Silicon (zsh), Python 3.12 |
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
| Topología RabbitMQ y librería (Fase 4, ADR-021) | La de la sección 11.2, con `pika==1.3.2` (síncrono, una conexión por publicación), mensajes persistentes, publisher confirms y `mandatory=True`. Hasta la Fase 5 el publicador declaraba toda la topología; desde la Fase 6 declara solo el exchange (ADR-032) |
| Publicación directa tras el commit (Fase 4, ADR-022) | **Reemplazada por ADR-026 en la Fase 5.** Puerto `UnitOfWork`; el caso de uso hacía guardar → commit → publicar. Si RabbitMQ fallaba tras el commit: 201 + log `ERROR` "Evento perdido" (double write) |
| Tabla `outbox_events` (Fase 5, ADR-024) | Columnas `id` (= `event_id`), `aggregate_type`, `aggregate_id`, `event_type`, `event_version`, `payload` (JSONB), `occurred_at`, `published_at`, `attempts`, `last_error`, `failed_at` (ADR-027); pendiente = `published_at IS NULL AND failed_at IS NULL`; índice parcial `ix_outbox_events_pending` sobre `occurred_at` con esa condición. `OutboxMessage` vive en la capa de aplicación (`app/application/outbox.py`). Los eventos publicados se conservan |
| Outbox Relay (Fase 5, ADR-025) | Proceso aparte (`python -m app.outbox_relay`) con `OUTBOX_RELAY_POLL_INTERVAL_SECONDS` (2) y `OUTBOX_RELAY_BATCH_SIZE` (10). `SELECT ... FOR UPDATE SKIP LOCKED`, un commit por lote, publicar y después marcar `published_at` (al menos una vez: puede haber duplicados, el consumidor es idempotente con `event_id`). Fallo temporal (`EventPublishError`) → `mark_failed` (`attempts + 1`, `last_error`), sigue pendiente y se detiene el lote, sin límite de intentos. Fallo permanente (ver ADR-027) → `mark_dead` y se continúa |
| Mensajes venenosos (Fase 5, ADR-027) | Payload ilegible o `event_type` desconocido = fallo permanente: `mark_dead` guarda `failed_at` y `last_error`, el mensaje deja de estar pendiente y no se reintenta (la fila se conserva para revisarla). `RelayResult` separa `failed` (temporales) de `dead` (descartados). Equivale, del lado del productor, a la DLQ de RabbitMQ |
| Registro del evento en la misma transacción (Fase 5, ADR-026) | Reemplaza a ADR-022. El caso de uso hace guardar → registrar el evento (`OutboxEventPublisher`, misma sesión) → commit. Si el registro falla, no hay commit (500). El relay reutiliza `RabbitMQEventPublisher` sin cambios y reconstruye el evento con `ItineraryCreatedEvent.from_dict`. Contrato y topología sin cambios |
| Plataforma serverless (Fase 6, ADR-008) | Imagen oficial de AWS Lambda `public.ecr.aws/lambda/python:3.12` con el Runtime Interface Emulator: solo requiere Docker, funciona en Windows y macOS (Apple Silicon) y se despliega sin cambios en AWS Lambda. API de invocación en `POST http://localhost:9000/2015-03-31/functions/function/invocations`. En local no hay escalado automático ni apagado sin eventos (limitación de la plataforma, no del código) |
| Modelo de programación de la función (Fase 6, ADR-028) | `handler(event, context)` en `app/handler.py`, sin estado entre invocaciones (solo se reutiliza el engine) y sin código de RabbitMQ. Hexagonal por dentro. Responde `PROCESSED`, `ALREADY_PROCESSED` o `REJECTED` (evento que no cumple el contrato v1). PostgreSQL no disponible → lanza `TransientError` (`translate_database_errors` envuelve toda la ejecución del caso de uso; el RIE lo informa como `errorType`); otros errores no se capturan. Comprobado: el RIE responde **HTTP 200 también en los errores** (solo el cuerpo trae `errorType`), y un cuerpo que no es JSON falla antes del handler con `Runtime.UnmarshalError` |
| Historial de notificaciones (Fase 6, ADR-029) | Contenedor `notification-postgres` (postgres:16-alpine, puerto 5434, usuario/clave `notification`, base `notification_db`), tabla `notification_history` con `event_id` único. Migraciones con Alembic desde el entorno virtual, no en cada invocación; la imagen no incluye Alembic (`requirements.txt` vs. `requirements-dev.txt`). Red Docker `notification-net` entre la función y su base. *Actualización (Fase 10, ADR-041):* en Docker Compose la red es `notification-data` y la migración corre en el contenedor `notification-migrations`; `notification-net` queda solo para el modo manual |
| Idempotencia y destinatario (Fase 6, ADR-030) | `INSERT ... ON CONFLICT (event_id) DO NOTHING` antes de enviar; si ya existía → `ALREADY_PROCESSED` sin reenviar. Sin `traveler_email` → `status = SKIPPED`, `recipient = NULL` y `status_reason` con el motivo |
| Fallos en el Event Trigger (Fase 6, ADR-031) | Éxito (`PROCESSED`, `ALREADY_PROCESSED`) → ACK. Permanente (mensaje que no es JSON, `REJECTED`) → `basic_reject(requeue=False)` → DLQ. Infraestructura (sin conexión, timeout de la invocación, HTTP 5xx, `errorType = TransientError`, o timeout de la propia función, que el RIE informa con HTTP 200 y el texto `Task timed out after N seconds`) → reintentos y después `basic_nack(requeue=True)` tras una pausa, sin límite y sin DLQ. Otro `errorType` → reintentos limitados y después a la DLQ, para no bloquear la cola (`prefetch_count=1`). Mismo criterio temporal/permanente de ADR-027. Reprocesamiento (6C): `python -m app.replay_dlq` (uno) o `--all` (los que había al empezar) devuelve los mensajes de la DLQ a la cola principal con el exchange por defecto, confirms y ACK en la DLQ después; quita `x-death` y suma `x-dlq-replays`. La DLQ tiene un segundo binding a la DLX con la routing key `notification.itinerary-created`, para que un mensaje reprocesado que vuelve a fallar no se pierda |
| Propiedad de la topología (Fase 6, ADR-032) | El publicador de Itinerary Service declara solo el exchange; el Event Trigger declara exchange, cola, binding, DLX y DLQ. Si el trigger no ha arrancado, `mandatory=True` devuelve el mensaje y el evento espera en la outbox |
| SonarCloud (PR #7, ADR-023) | Análisis de calidad con **Automatic Analysis** (sin paso en GitHub Actions), configurado en `.sonarcloud.properties` (desde la 6C analiza también `serverless/`). No importa cobertura. Su Quality Gate no forma parte por ahora del acuerdo de merge (check "Pruebas" + 1 aprobación) |
| API Gateway (Fase 7, ADR-009) | **Nginx** como gateway puro en Docker (`gateway/Dockerfile` sobre `nginx:1.30.6-alpine`; desde la Fase 9, `nginx:1.30.6-alpine-otel` con `gateway/nginx.conf` propio, ADR-036; plantilla `gateway/templates/default.conf.template` con `envsubst` de la imagen oficial), puerto 8000. `/api/airports...` → Airport Service y `/api/itineraries...` → Itinerary Service, quitando `/api` (y `proxy_redirect` para las redirecciones). Direcciones por variables `AIRPORT_SERVICE_UPSTREAM` / `ITINERARY_SERVICE_UPSTREAM` (`host.docker.internal:8001/8002` en la Fase 7; nombres de contenedor en la Fase 10). Reenvía `Authorization` sin validarlo (nunca en el log). `X-Correlation-ID`: se reenvía si cumple `^[A-Za-z0-9._-]{1,128}$`; si no, se genera con forma de UUID. Timeouts: conexión 2 s, lectura 15 s, `proxy_next_upstream off`, `max_fails=0`. Errores propios en el formato de la sección 10.2: 502 `UPSTREAM_UNAVAILABLE`, 504 `UPSTREAM_TIMEOUT`, 404 `ROUTE_NOT_FOUND`, 413 `PAYLOAD_TOO_LARGE`; los errores de los servicios pasan sin cambios (`proxy_intercept_errors off`). Rate limiting (7B): por IP, 10 r/s, ráfaga 20, `nodelay`, solo `/api/`, 429 `RATE_LIMIT_EXCEEDED` con `Retry-After`. `GET /health` propio, `/` sirve el frontend (Fase 8), sin CORS, Swagger no se expone por el gateway |
| Frontend (Fase 8, ADR-033) | Vanilla HTML/CSS/JS con ES modules, sin build toolchain, servido como estáticos por Nginx desde `frontend/` (copiado en la imagen del gateway, `location / { try_files ... }`, rutas no encontradas → 404 `ROUTE_NOT_FOUND` en JSON). Mapa de aeropuertos con `scattergeo` de Plotly 4.3.0 (bundle parcial `plotly-geo.min.js`, 1.4 MB, local para uso sin internet, marcado como binario en `.gitattributes`). CRUD de itinerarios con formulario y tabla; `datetime-local` → ISO 8601 con offset del navegador (ADR-017). Todo texto de datos con `textContent` (nunca `innerHTML`). Errores del gateway con `correlation_id` y botón "Copiar" en 5xx. Pruebas pytest en `gateway/tests` (misma suite del gateway). El contexto de build del gateway cambia a la raíz del repositorio: `docker build -t api-gateway -f gateway/Dockerfile .`. *Actualización (mejora del frontend):* tema claro/oscuro (variables CSS, `prefers-color-scheme` y botón con `localStorage`), fuente D-DIN local, avisos con `aria-live`, confirmación con `<dialog>`, validación con las reglas de ADR-015, buscador de aeropuertos y ruta en el mapa (nota en ADR-033) |
| Logs JSON (Fase 9, ADR-034) | `python-json-logger==4.2.0` en los cuatro componentes Python y en la función. Campos `timestamp`, `level`, `service`, `logger`, `message`, `correlation_id`, `trace_id`, `span_id`; filtros `CorrelationIdFilter` (de una `ContextVar` por solicitud) y `OTelContextFilter` (span activo). `configure_logging(log_level, service_name)` idempotente sobre el logger `app`; variable `LOG_LEVEL`. Desde el cierre de la Fase 9 vive en `libs/observability` (ADR-040) |
| Trazas distribuidas (Fase 9, ADR-035) | `opentelemetry-sdk==1.45.2`, instrumentadores `0.66b2` según el componente (FastAPI, httpx, SQLAlchemy, pika, logging) y exportador OTLP gRPC. `setup_tracing(service_name, instrumentors, batch)`: `BatchSpanProcessor` en producción e `InMemorySpanExporter` en las pruebas. `OTEL_ENABLED=false` desactiva el envío; `OTEL_EXPORTER_OTLP_ENDPOINT` (por defecto `http://localhost:4317`). Propagación W3C (`traceparent`) con el propagador por defecto de OpenTelemetry |
| Instrumentación del gateway (Fase 9, ADR-036) | Imagen `nginx:1.30.6-alpine-otel` con `ngx_otel_module`. Se provee `gateway/nginx.conf` propio con `load_module modules/ngx_otel_module.so;` antes del bloque `events {}` (la imagen no lo carga por defecto). `otel_trace_context propagate` inyecta el `traceparent` del span hijo al upstream; no se usa `proxy_set_header traceparent` (sobrescribiría el span hijo con el original del cliente). |
| `traceparent` en la outbox (Fase 9, ADR-037) | Columna `traceparent` (`VARCHAR(55)`, nullable) en `outbox_events` (migración `e6f0a4b8c1d9`). `OutboxEventPublisher` guarda el contexto W3C de la solicitud; el relay lo restaura antes de publicar; el trigger lo lee de los headers AMQP y lo inyecta en el evento; el handler de la función lo restaura. Así una traza cruza el proceso del relay y RabbitMQ |
| Métricas (Fase 9, ADR-038) | `prometheus-client==0.21.1`. Airport e Itinerary Service: `metrics_middleware` (`http_requests_total`, `http_request_duration_seconds`, con la plantilla de la ruta) y `/metrics`; `itineraries_created_total`. Outbox Relay (9101) y Event Trigger (9102) con `start_http_server` y contadores propios. Prometheus `v2.55.0` cada 15 s y Grafana `11.3.1` con datasource y dashboard cargados al arrancar |
| Jaeger (Fase 9, ADR-039) | `jaegertracing/jaeger:2.23.0` (amd64 y arm64), OTLP gRPC en 4317 e interfaz en 16686, trazas en memoria (se pierden al reiniciar) |
| Paquete compartido de observabilidad (cierre Fase 9, ADR-040) | `libs/observability`: Microservice Chassis Pattern con logging, trazas y métricas HTTP comunes. Instalado con `-e ../../libs/observability` en cada `requirements.txt`. El Dockerfile de SendNotificationFunction cambia el contexto de build a la raíz del repositorio para incluir `libs/`. Los Dockerfiles de Airport e Itinerary Service harán lo mismo en la Fase 10. *Actualización (Fase 10, ADR-041):* las imágenes de Airport, Itinerary y el trigger usan el contexto en la raíz, pero no instalan el paquete con pip: copian `libs/observability/observability` y lo agregan al `PYTHONPATH` (la imagen de la función sí lo instala con pip) |
| Docker Compose (Fase 10, ADR-041) | `docker-compose.yml` en la raíz (proyecto `sistema-itinerarios`, 15 servicios) con los puertos de la sección 7.6. Imágenes propias sobre `python:3.12-slim` con usuario `appuser`, contexto de build en la raíz y `Dockerfile.dockerignore` por imagen (lista blanca): Airport Service, Itinerary Service (**una imagen para la API, `outbox-relay` e `itinerary-migrations`**), Event Trigger y `Dockerfile.migrations` de la función (imagen de la función sin Alembic, ADR-029). Las imágenes instalan solo `requirements-lock.txt` (todas las dependencias, también las transitivas, con hashes; generado con `python scripts/lock_requirements.py` a partir de `requirements-runtime.txt`, o de `requirements-migrations.txt` en la función) con `pip install --only-binary :all: --require-hashes` (reglas S8541 y S8544 de SonarCloud); `libs/observability` va por `PYTHONPATH`, sin pip. `requirements.txt` sigue siendo el archivo del entorno virtual y del CI. Migraciones como contenedores de una sola ejecución (`service_completed_successfully`); healthchecks de PostgreSQL, RabbitMQ, Redis, servicios FastAPI (Python `urllib`) y gateway (`wget`); el gateway solo espera `service_started`. Redes `itinerary-data` y `notification-data` (cada base solo con su servicio dueño; reemplaza a `notification-net`). `OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317`. Observabilidad siempre activa; Prometheus con `prometheus.compose.yml` (`prometheus.yml` se conserva para el modo manual). `stop_signal: SIGINT` en el relay y el trigger. Volúmenes para las dos bases y RabbitMQ (`hostname: rabbitmq`). `.env.example` en la raíz con variables opcionales. Modo manual conservado para desarrollo. Job de CI "Docker Compose". El `.dockerignore` antiguo de la función se borró en el cierre de la Fase 11 (lo reemplaza `Dockerfile.dockerignore`) |
| IP de los servicios en el gateway con Compose (cierre Fase 11, ADR-041) | Se **mantiene la limitación documentada**: Nginx resuelve los upstreams al arrancar, así que si un contenedor de servicio se recrea con otra IP el gateway responde 502 `UPSTREAM_UNAVAILABLE` hasta `docker compose restart api-gateway`. No se usa `resolver 127.0.0.11` con variables en `proxy_pass`: cambiaría ADR-009 y las pruebas del gateway para un caso que solo aparece al reconstruir un servicio con el sistema encendido |
| Evidencias (Fase 12) | `docs/evidencias/` con un índice (`README.md`) y 18 evidencias de una misma sesión: 7 salidas de terminal (`scripts/evidencias_terminal.py`, librería estándar) y 11 capturas web (`scripts/capturar_evidencias.py`, Playwright en `scripts/.venv`). Identificadores únicos por sesión. SonarCloud (19) y GitHub Actions (20) los captura el equipo. Datos de ejemplo (`@example.com`). *Actualización (mejora del frontend):* 10 a 14 regeneradas el 2026-11-23 y nueva 21 (modo oscuro a 1280 px) |
| `GenerateItineraryReportFunction` (cierre Fase 11, ADR-043) | **No se implementa** por decisión de alcance. Era opcional en la Fase 6; `SendNotificationFunction` ya demuestra el modelo FaaS completo (evento → Event Trigger → función, idempotencia, DLQ) |
| Estrategia de pruebas (Fase 11, ADR-042) | Pirámide de cinco niveles: unitarias, integración (SKIPPED sin el servicio), contrato, gateway (contenedor propio) y punta a punta. Las pruebas de integración de Itinerary Service y de la función usan `<base>_test` (`itinerary_db_test`, `notification_db_test`) en el mismo servidor, creada y migrada por `tests/integration/database_setup.py` (`alembic/env.py` acepta `config.attributes["connection"]`); un error al migrar falla, solo la falta de PostgreSQL da SKIPPED. `libs/observability` tiene pruebas propias y job de CI. Contratos: `docs/openapi/airport-service.json` (Airport lo compara con su API; se regenera con `UPDATE_CONTRACTS=1`) que Itinerary verifica como consumidor, y AsyncAPI verificado también por la función (consumidor). E2E en `tests/e2e` sobre `docker compose -f docker-compose.yml -f docker-compose.e2e.yml` (simulador de API Colombia), por el gateway; leen las bases con `docker compose exec ... psql`; incluyen una traza en Jaeger con los seis componentes; el job "Docker Compose" las ejecuta (`COMPOSE_FILE` con los dos archivos). Advertencias de Starlette (`httpx2`) y pika (`utcfromtimestamp`) filtradas en `pytest.ini` por mensaje y origen, sin migrar librerías. Las pruebas del gateway fijan `host.docker.internal` a su IPv4 con `--add-host` |

### 9.2. Propuestas (confirmar con el usuario antes de implementarlas)

Ninguna por ahora (el contrato del evento y la topología de RabbitMQ se aceptaron en la Fase 4:
ADR-020 y ADR-021).

### 9.3. Pendientes (no implementar sin decisión del usuario)

| Decisión | Opciones | Se necesita en |
|---|---|---|
| Protección de `main` y de las ramas `fase-*` | Se configura en GitHub (*Settings → Rules → Rulesets* o *Branches*). Propuesta: en `main`, exigir PR con 1 aprobación y el check "Pruebas", y bloquear push forzado y borrado; en `fase-*`, bloquear push, push forzado y borrado (solo lectura). Hoy son solo acuerdos del equipo. **La decide y la configura el dueño del repositorio en GitHub**; Claude Code no la configura | Cuando el dueño del repositorio lo decida |

Cuando una decisión se confirme, actualiza esta sección y `docs/06-decisiones-arquitectonicas.md`
(explicando el cambio antes de hacerlo).

---

## 10. Contratos HTTP

### 10.1. Endpoints

Los endpoints de Airport Service y de Itinerary Service están **aceptados** (ADR-012, ADR-019). El 504 por timeout
se agregó en la Fase 2 (Airport, ADR-014) y en la Fase 3 (Itinerary, ADR-019); el contrato publicado de Airport Service
está en `docs/openapi/airport-service.json` (Fase 11).

| Servicio | Método y ruta | Éxito | Errores |
|---|---|---|---|
| Airport | `GET /airports` | 200 | 502, 503, 504 |
| Airport | `GET /airports/{id}` | 200 | 404, 422, 502, 503, 504 |
| Airport | `GET /airports/map-data` | 200 (arrays para Plotly) | 502, 503, 504 |
| Itinerary | `POST /itineraries` | 201 | 422, 503, 504 |
| Itinerary | `GET /itineraries` | 200 | — |
| Itinerary | `GET /itineraries/{id}` | 200 | 404, 422 (el id no es un UUID) |
| Itinerary | `PUT /itineraries/{id}` | 200 | 404, 422, 503, 504 |
| Itinerary | `DELETE /itineraries/{id}` | 204 | 404, 422 (el id no es un UUID) |
| Todos | `GET /health` | 200 | — |
| Todos | `GET /metrics` | 200 | — (Fase 9) |

En el Gateway (puerto 8000, ADR-009): `/api/airports/...` → Airport Service y `/api/itineraries/...` → Itinerary Service
(sin el prefijo `/api`); `GET /health` propio; `/` reservada para el frontend; cualquier otra ruta → 404 `ROUTE_NOT_FOUND`.

El endpoint `map-data` tiene formato de presentación, así que vive en la capa `api`, no en el dominio.

### 10.2. Códigos de error (aceptado)

| Situación | Código |
|---|---|
| Recurso no encontrado | 404 |
| Validación de datos o aeropuerto inexistente al crear un itinerario | 422 |
| El proveedor externo respondió algo inesperado | 502 |
| Dependencia no disponible (API Colombia, Airport Service) | 503 |
| Timeout de una dependencia (Fase 2) | 504 |
| Gateway: la ruta no existe (Fase 7) | 404 `ROUTE_NOT_FOUND` |
| Gateway: el cuerpo supera 1 MB (Fase 7) | 413 `PAYLOAD_TOO_LARGE` |
| Gateway: se superó el límite de solicitudes (Fase 7) | 429 `RATE_LIMIT_EXCEEDED` |
| Gateway: el servicio no acepta la conexión (Fase 7) | 502 `UPSTREAM_UNAVAILABLE` |
| Gateway: el servicio no responde a tiempo (Fase 7) | 504 `UPSTREAM_TIMEOUT` |

Los errores de los servicios pasan por el gateway sin cambios (ADR-009, actualización de ADR-012).

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

| Fase | Nombre | Contenido | Estado |
|---|---|---|---|
| 0 | Planificación y arquitectura | Objetivos, alcance, arquitectura, dominio, comunicación, diagramas y decisiones (`docs/01` a `docs/06`) | Completada (sin etiqueta: es anterior a la regla de etiquetas) |
| 1 | Airport Service | FastAPI, hexagonal, dominio, puerto, Adapter, cliente API Colombia, traducción externo → interno, endpoints, errores, Swagger, Pydantic, tests básicos. **Sin Redis ni circuit breaker.** Demostrar: cliente → Airport Service → Adapter → API Colombia | Completada (etiqueta `fase-1`) |
| 2 | Resiliencia y caché | Redis, caché, timeout, retry, exponential backoff, circuit breaker, fallback. Explicar cada mecanismo. Probar: API funciona, API tarda demasiado, API no responde, consultas repetidas | Completada (etiqueta `fase-2`) |
| 3 | Itinerary Service | FastAPI, hexagonal, DDD básico, entidad Itinerary, PostgreSQL, SQLAlchemy, Pydantic, Alembic, CRUD completo, errores, Swagger. Validación HTTP de aeropuertos contra Airport Service antes de guardar | Completada (etiqueta `fase-3`) |
| 4 | Eventos y RabbitMQ | `ItineraryCreatedEvent`, exchange, cola, routing key, contrato formal, AsyncAPI. Explicar: llamada HTTP vs evento vs evento de dominio vs evento de integración. Publicación directa tras el commit (para mostrar luego el problema de double write) | Completada (etiqueta `fase-4`) |
| 5 | Transactional Outbox | Itinerario + evento en la misma transacción, worker/relay que publica en RabbitMQ. Explicar el problema de double write | Completada (etiqueta `fase-5`) |
| 6 | Serverless | `SendNotificationFunction`: recibe el evento, simula la notificación, guarda historial, maneja errores. Explicar por qué es FaaS. Opcional: `GenerateItineraryReportFunction` (no implementada por alcance, ADR-043) | Completada (etiqueta `fase-6`) |
| 7 | API Gateway | Punto único de entrada, enrutamiento, sin lógica de negocio, rate limiting básico, preparar propagación de JWT | Completada (etiqueta `fase-7`) |
| 8 | Frontend | Consultar aeropuertos, mapa con Plotly JS, CRUD de itinerarios. Solo vía nuestros servicios | Completada (etiqueta `fase-8`) |
| 9 | Observabilidad | Logs JSON, correlation ID, `trace_id`, `span_id`, OpenTelemetry, Jaeger, Prometheus, Grafana. Demostrar el recorrido completo Frontend → Gateway → Itinerary → Airport → BD → Evento → RabbitMQ → Función | Completada (etiqueta `fase-9`) |
| 10 | Docker y Docker Compose | Contenedores para todos los componentes, `docker-compose.yml`, cómo levantar y detener todo | Completada (etiqueta `fase-10`) |
| 11 | Pruebas | Unit, integración, API, Adapter, CRUD, comunicación HTTP, eventos, flujo completo. E2E sobre Docker Compose (Testcontainers se descartó, ADR-042) | Completada (etiqueta `fase-11`) |
| 12 | Documentación y entrega | README profesional con todos los diagramas (componentes, clases, relacional, secuencia, despliegue), instalación, ejecución, variables de entorno, endpoints, eventos, evidencias y pruebas | Completada (etiqueta `fase-12`) |

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

### 12.5. Plan de la Fase 5 (entregas)

Rama `fase-5-transactional-outbox`. Una pausa al final de cada entrega, antes del commit.

| Entrega | Contenido | Verificación |
|---|---|---|
| **5A** | ADR-024 a ADR-026 (y ajustes de ADR-006, ADR-013, ADR-022), `OutboxEventORM` y migración `b7c2d9e1f4a6`, `OutboxMessage`, `ItineraryCreatedEvent.from_dict`, `OutboxEventPublisher`, caso de uso guardar → registrar → commit, ensamblaje en `dependencies.py`, pruebas | `pytest -v` pasa; `alembic upgrade head` aplica la migración; pruebas de `tests/integration/test_outbox_integration.py` pasan con PostgreSQL |
| **5B** | Puerto `OutboxRepository`, `SqlAlchemyOutboxRepository` (`SKIP LOCKED`), `OutboxRelay` en `application`, proceso `app/outbox_relay.py`, variables del relay, pruebas unitarias con fakes e integración (SKIPPED sin PostgreSQL o RabbitMQ) | Pruebas del relay pasan sin PostgreSQL ni RabbitMQ |
| **5C** | Primer commit: mensajes venenosos (ADR-027, columna `failed_at` con la migración `c4d8e2f6a9b1`, `mark_dead`, índice parcial ajustado, pruebas). Después: `docs/04` (Outbox, duplicados e idempotencia), diagramas de `docs/05`, descripción en AsyncAPI (sin cambiar el contrato), README del servicio con la demostración del double write resuelto, revisión del job de CI, estado de CLAUDE.md | Con RabbitMQ detenido: 201 y evento pendiente; al levantarlo, el relay lo publica en la cola |

### 12.6. Plan de la Fase 6 (entregas)

Rama `fase-6-serverless`. Una pausa al final de cada entrega, antes del commit.

| Entrega | Contenido | Verificación |
|---|---|---|
| **6A** | ADR-008 (decidida), ADR-028 a ADR-030, `serverless/send-notification-function`: dominio (`NotificationRecord`), caso de uso, puertos, `SimulatedEmailSender`, repositorio del historial, handler de Lambda, esquema del evento, Alembic con la migración de `notification_history`, `Dockerfile`, eventos de ejemplo y pruebas | `pytest -v` pasa; invocación con `curl.exe` contra el RIE en el puerto 9000 (`PROCESSED`, `ALREADY_PROCESSED`, `SKIPPED`, `REJECTED`, `TransientError`) |
| **6B** | ADR-031 y ADR-032, `serverless/event-trigger` (consumo, invocación, ACK/NACK, reintentos, DLQ, declaración de la topología), cambio de la topología del publicador de Itinerary Service (solo el exchange), pruebas unitarias y de integración (SKIPPED sin RabbitMQ, PostgreSQL o la función) | Pruebas del trigger pasan sin servicios |
| **6C** | Documentación (FaaS, diagramas, AsyncAPI con la operación `receive` y la DLQ, README de cada componente y README raíz), jobs de CI de la función y del trigger, `serverless` en SonarCloud, demostración de punta a punta (incluye evento duplicado, evento en la DLQ y evento que espera en la outbox mientras el trigger no ha arrancado). Aislar las pruebas de integración del trigger: hoy vacían (purge) la cola `notification.itinerary-created` y su DLQ reales, así que correr `pytest` durante una demostración borra sus mensajes. Deben usar un vhost de pruebas o un exchange y colas de prueba con nombres propios, eliminados al terminar; si alguna prueba no puede aislarse, se omite cuando la cola real tenga mensajes, y se documenta | Registro en `notification_history` tras crear un itinerario; las pruebas del trigger no cambian el contenido de la cola real ni de la DLQ |

### 12.7. Plan de la Fase 7 (entregas)

Rama `fase-7-api-gateway`. Una pausa al final de cada entrega, antes del commit.

| Entrega | Contenido | Verificación |
|---|---|---|
| **7A** | ADR-009 aceptada, carpeta `gateway/` (`Dockerfile`, `.dockerignore`, `templates/default.conf.template`, `.env.example`, README básico): enrutamiento, `X-Correlation-ID`, reenvío de `Authorization`, timeouts, `/health`, `/` y errores en JSON | `nginx -t` correcto; demostración con `curl` contra los dos servicios (incluye 404 del servicio vs. 404 del gateway y 502 con un servicio apagado) |
| **7B** | Rate limiting con 429 en JSON. Pruebas de integración en `gateway/tests` (con `gateway/requirements-dev.txt`: pytest y httpx, entorno virtual propio): pytest levanta **su propio contenedor del gateway** contra un servidor eco de Python (enrutamiento, quitar `/api`, `Authorization`, `X-Correlation-ID` válido e inválido, 429, 502 con un puerto cerrado, 504 con un eco lento y un timeout corto), más pruebas *smoke* solo con `GET` contra el gateway real (omitidas si no está corriendo). Todo se omite sin Docker | Pruebas pasan; no cambian datos reales ni consumen el límite del gateway real |
| **7C** | Documentación (`docs/02`, `docs/05`, ADR-012 y sección 10.2 con los errores del gateway, título "API Gateway" en lugar de "API Gateway / BFF", README del gateway y README raíz con el nuevo orden de arranque), job de CI que valide la configuración (`nginx -t`) y ejecute las pruebas de la 7B, demostración de punta a punta pasando por el gateway | CI pasa; recorrido Gateway → Itinerary → Airport → outbox → RabbitMQ → función |

### 12.8. Plan de la Fase 8 (entregas)

Rama `fase-8-frontend`. Una pausa al final de cada entrega, antes del commit.

| Entrega | Contenido | Verificación |
|---|---|---|
| **8A** | ADR-033, carpeta `frontend/` (`index.html`, `css/style.css`, `js/api.js`, `js/main.js`), gateway actualizado para servir estáticos desde la raíz del repositorio (`Dockerfile.dockerignore`, contexto raíz, `location / { try_files }`, `@route_not_found` en JSON), `test_routing.py` actualizado, `test_static.py` nuevo, CI actualizado | `nginx -t` correcto; GET / devuelve HTML; GET /no-existe.html devuelve 404 JSON |
| **8B** | Mapa de aeropuertos: `plotly-geo.min.js` 4.3.0 (local, 1.4 MB), `airports.js` con `scattergeo` centrado en Colombia, spinner, conteo real, tooltip por tipo | Mapa con 51 aeropuertos; colores por tipo; tooltip correcto |
| **8C** | CRUD de itinerarios: `itineraries.js` con formulario 2 columnas, desplegables de aeropuertos, tabla, editar inline, eliminar con `confirm()`, `datetime-local` → ISO 8601 con offset, errores con `correlation_id` y botón copiar | Crear, editar y eliminar itinerarios; errores del servicio en banner |

### 12.9. Plan de la Fase 9 (entregas)

Rama `fase-9-observabilidad`. Este plan se agregó en la Fase 12 a partir de lo registrado en la sección 15 (durante la
Fase 9 no quedó escrito aquí).

| Entrega | Contenido | Verificación |
|---|---|---|
| **9A** | ADR-034: logs JSON con `python-json-logger` en los cuatro componentes Python (`configure_logging`, `CorrelationIdFilter`, `OTelContextFilter`) | Pruebas de `test_logging_config.py` |
| **9B** | ADR-035 a ADR-037 y ADR-039: OpenTelemetry con exportador OTLP a Jaeger, gateway con `nginx:1.30.6-alpine-otel`, columna `traceparent` en `outbox_events` (migración `e6f0a4b8c1d9`) y propagación por relay, RabbitMQ, trigger y función | Pruebas de propagación en la outbox y el relay; traza en Jaeger |
| **9C** | ADR-038: métricas con `prometheus-client` (HTTP, negocio, relay y trigger), Prometheus y Grafana con dashboard preconfigurado | Destinos de Prometheus `up`; dashboard en Grafana |
| **9D** | Documentación de la fase (`docs/02`, `docs/05`, `docs/06`, README raíz y de los componentes) | — |
| **Cierre** (`docs/cierre-fase-9`) | ADR-040: `libs/observability` (Microservice Chassis Pattern) por la duplicación que detectó SonarCloud; corrección de la carga del módulo OTel del gateway | CI del gateway y SonarCloud pasan |

### 12.10. Plan de la Fase 10 (entregas)

Rama `fase-10-docker-compose`. Una pausa al final de cada entrega.

| Entrega | Contenido | Verificación |
|---|---|---|
| **10A** | Dockerfiles de Airport Service, Itinerary Service (API, relay y migraciones), Event Trigger y `Dockerfile.migrations` de la función, con un `Dockerfile.dockerignore` por imagen (incluido el de la imagen de la función) | Las cinco imágenes se construyen; contexto de build pequeño; `whoami` → `appuser` |
| **10B** | `docker-compose.yml` (15 servicios, migraciones de una sola ejecución, healthchecks, redes por base, volúmenes, `stop_signal: SIGINT`), `prometheus.compose.yml`, `.env.example` en la raíz | `docker compose up -d --build`: migraciones `Exited (0)`, servicios `healthy`, recorrido de punta a punta por el gateway hasta `notification_history` |
| **10C** | ADR-041, `docs/02` (sección 7), `docs/05` (despliegue y orden de arranque), README raíz (arranque con Compose, modo manual, demostraciones con Compose), README de los cinco componentes, job de CI "Docker Compose", estado de CLAUDE.md | Job "Docker Compose" pasa en el PR |

### 12.11. Plan de la Fase 11 (entregas)

Rama `fase-11-pruebas`. Por decisión del usuario, las cuatro entregas se hicieron seguidas, con un commit por entrega
y una sola pausa al final.

| Entrega | Contenido | Verificación |
|---|---|---|
| **11A** | Bases propias de las pruebas de integración (Itinerary y función), pruebas y job de CI de `libs/observability`, IPv4 de `host.docker.internal` en las pruebas del gateway | Integración pasa con la base real sin migrar; `itinerary_db_test` y `notification_db_test` creadas |
| **11B** | Pruebas de contrato: `docs/openapi/airport-service.json` (proveedor y consumidor) y AsyncAPI en la función | Pruebas de contrato pasan |
| **11C** | `docker-compose.e2e.yml` con el simulador de API Colombia, `tests/e2e` y su paso en el job "Docker Compose" | 14 E2E pasan dos veces seguidas y no dejan itinerarios |
| **11D** | Filtro de advertencias, ADR-042, README raíz (sección "Pruebas") y de los componentes, estado de CLAUDE.md | Siete suites sin fallos, sin omitidas y sin advertencias con todo encendido |

### 12.12. Plan de la Fase 12 (entregas)

Rama `fase-12-documentacion`. Una pausa al final de cada entrega, antes del commit. Reglas acordadas: el README no queda
con secciones vacías entre entregas; en "Arquitectura" cada concepto es corto (qué es y por qué se usa, dónde está en el
código y enlace al documento de `docs/` que lo explica); el contenido que sale del README se mueve, no se borra; los
totales de pruebas se confirman ejecutándolas.

| Entrega | Contenido | Verificación |
|---|---|---|
| **12A** | Diagramas de clases (Airport, Itinerary API, Outbox Relay, función) y relacional (`itinerary_db`, `notification_db`) en `docs/05`, sacados del código y de las migraciones; `docs/07-ejecucion-manual.md`, `docs/08-demostraciones.md` y `docs/10-historial-de-fases.md` con el contenido movido del README; README con el contenido existente en el nuevo orden; enlaces actualizados | Los 15 diagramas de `docs/05` se dibujan sin errores; ningún enlace interno roto |
| **12B** | README completo (arquitectura por conceptos, diagramas, variables de entorno, endpoints por el gateway, eventos, limitaciones conocidas, resumen de ADR), verificación de la documentación contra el código con la lista de contradicciones, totales de pruebas ejecutándolas, grupos C (estados de ADR) y D (CLAUDE.md 7.5, 7.6 y 12; resúmenes del README) | Cada contradicción listada y corregida; totales de pruebas confirmados |
| **12C** | `docs/evidencias/` (índice de capturas y referencias en el README), `docs/09-guia-sustentacion.md`, revisión final de enlaces y del orden de lectura, estado de CLAUDE.md | Ningún enlace roto; orden de lectura revisado |

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
- **Fase 5:** completada y **fusionada en `main`** (PR #10, merge `a711afa`) con la **etiqueta `fase-5`**.
  La rama `fase-5-transactional-outbox` se conserva como archivo de solo lectura.
  - Entrega **5A** completada (commit `599f4e0`): ADR-024 a ADR-026, tabla `outbox_events`
    (migración `b7c2d9e1f4a6`), `OutboxMessage`, `ItineraryCreatedEvent.from_dict`, `OutboxEventPublisher`
    y `CreateItineraryUseCase` con guardar → registrar el evento → commit (desaparece "Evento perdido").
    La API ya no publica en RabbitMQ: los eventos quedan pendientes hasta el relay de la 5B.
    Total del servicio: **114 pruebas pasan, 13 omitidas** sin PostgreSQL ni RabbitMQ; con PostgreSQL
    (migración aplicada): **126 pasan, 1 omitida** (la de RabbitMQ).
  - Entrega **5B** completada (commit `266d177`): puerto `OutboxRepository` y `SqlAlchemyOutboxRepository`
    (`FOR UPDATE SKIP LOCKED`, marcas con `UPDATE`), `OutboxRelay` en `app/application/outbox_relay.py`
    (un commit por lote, fallo de publicación detiene el lote, mensaje ilegible se marca y se continúa),
    proceso `python -m app.outbox_relay` (`app/outbox_relay.py`: un ciclo fallido no detiene el proceso,
    sin pausa tras un lote completo, logs de pika en `CRITICAL`), variables `OUTBOX_RELAY_POLL_INTERVAL_SECONDS`
    y `OUTBOX_RELAY_BATCH_SIZE`. El fixture `rabbitmq_channel` pasa a `tests/integration/conftest.py`.
    Total del servicio: **138 pasan, 21 omitidas** sin PostgreSQL ni RabbitMQ; **159 pasan** con ambos.
  - Entrega **5C** completada:
    - Primer commit (`fd686a1`): mensajes venenosos (ADR-027). Columna `failed_at` (migración `c4d8e2f6a9b1`,
      índice parcial `published_at IS NULL AND failed_at IS NULL`), `mark_dead` en `OutboxRepository`, `RelayResult.dead`.
    - Segundo commit (`docs: documenta el Transactional Outbox...`): `docs/04` sección 7 (flujo, Outbox Relay, al menos una vez,
      duplicados e idempotencia; mensajes venenosos pasa a 7.4) y secciones 3.3, 3.4 y 6 marcadas como históricas
      o actualizadas; diagramas de componentes, general y de secuencia de `docs/05`; descripción de la operación en
      `asyncapi.yaml` (contrato sin cambios); README del servicio (dos procesos, migraciones, variables del relay y
      demostración del double write resuelto) y README raíz. El job de CI no necesita cambios (las pruebas de
      integración se omiten sin PostgreSQL ni RabbitMQ).
    - Demostración real hecha el 2026-11-08: con RabbitMQ detenido, `POST /itineraries` → 201 y evento pendiente;
      el relay falló 9 veces sin perderlo y lo publicó al volver RabbitMQ (`message_id` = `event_id`).
    - Total del servicio: **167 pasan** con PostgreSQL y RabbitMQ; **143 pasan, 24 omitidas** sin ellos.
- **Fase 6:** completada y **fusionada en `main`** (PR #11, merge `1f5d8eb`) con la **etiqueta `fase-6`**.
  La rama `fase-6-serverless` se conserva como archivo de solo lectura.
  - Entrega **6A** completada: ADR-008 (imagen de AWS Lambda con RIE) y ADR-028 a ADR-030.
    `serverless/send-notification-function` con dominio (`NotificationRecord`, SENT/SKIPPED), caso de uso
    `NotifyItineraryCreatedUseCase` (insertar con `ON CONFLICT DO NOTHING RETURNING id` → enviar → commit),
    puertos, `SimulatedEmailSender`, repositorio con `TransientError`, handler de Lambda y esquema del contrato v1,
    Alembic (migración `d1e5f7a3b9c2`, tabla `notification_history`), `Dockerfile` y eventos de ejemplo en `events/`.
    Demostración real con `curl.exe` contra el RIE: `PROCESSED`/`SENT`, `ALREADY_PROCESSED`, `SKIPPED`, `REJECTED` y
    `TransientError` con PostgreSQL detenido. Total: **59 pruebas pasan** con PostgreSQL; **53 pasan, 6 omitidas**
    sin él.
  - Entrega **6B** completada:
    - ADR-031 (política del Event Trigger, relación con ADR-027) y ADR-032 (propiedad de la topología); correcciones
      en ADR-021, ADR-027, `docs/04` y el README de Itinerary Service.
    - Itinerary Service: `topology.py` declara solo el exchange (`declare_exchange`); las pruebas con canal falso
      comprueban que el publicador no declara colas; el fixture `rabbitmq_channel` declara la cola en el papel del
      consumidor; nueva prueba de integración "sin cola del consumidor, el evento espera en la outbox". El relay no
      cambió: ya trataba `UnroutableError` como fallo temporal. Total del servicio: **167 pasan** con PostgreSQL y
      RabbitMQ; **142 pasan, 25 omitidas** sin ellos.
    - `serverless/event-trigger` (`python -m app.main`): `DeliveryHandler` y `RetryPolicy` en `application`,
      `LambdaFunctionInvoker` (httpx; lee código HTTP y `errorType`), consumidor pika con ACK manual,
      `prefetch_count=1`, `connection.sleep` en las esperas, declaración de la topología en cada conexión,
      reconexión ante pérdida de RabbitMQ y parada con Ctrl+C. Archivos `demo/` para publicar un evento inválido y
      uno que no es JSON por la API del panel. Total: **62 pasan** con RabbitMQ y la función; **50 pasan, 12
      omitidas** sin ellos.
    - Demostración real (2026-11-11): trigger apagado desde el principio (evento en la outbox con `UnroutableError`,
      publicado al arrancar el trigger), caso normal, duplicado (`ALREADY_PROCESSED`, 1 sola fila), función apagada y
      `notification-postgres` apagado (reintentos sin límite, nunca a la DLQ), evento inválido y mensaje no JSON
      (directo a la DLQ, `x-death` con `reason=rejected`) y reconexión tras reiniciar RabbitMQ.
  - Entrega **6C** completada:
    - Pruebas de integración del trigger **aisladas**: `QueueTopology` (nombres de la topología) con una copia
      `test-<id>.` declarada una vez por sesión, vaciada entre pruebas y borrada al final. Ninguna prueba vacía ni
      consume la cola real ni su DLQ (comprobado con mensajes en la DLQ real y el trigger real encendido); la prueba
      de compatibilidad con la topología real se omite si la cola real no existe, para no crearla.
    - Reprocesamiento de la DLQ: `python -m app.replay_dlq [--all]` (`DeadLetterReplayer`), con pruebas unitarias e
      de integración aisladas. Una prueba detectó que un mensaje reprocesado que volvía a fallar **se perdía**
      (la DLX no tenía binding para la routing key `notification.itinerary-created`): se agregó ese segundo binding
      a la DLQ.
    - El trigger registra solo la primera línea del `errorMessage` de la función (antes copiaba el SQL con sus
      parámetros, incluido el correo del viajero).
    - Documentación: FaaS y Event Trigger en `docs/04` (sección 8), diagramas de `docs/05` (general, componentes,
      secuencia, fallos del consumidor, despliegue), `docs/02` y `docs/03` (NotificationRecord), AsyncAPI 1.1.0
      (operación `receive` completa y canal de la DLQ, contrato sin cambios) con la prueba
      `tests/test_asyncapi_topology.py` del trigger, README de la función y del trigger, README raíz (orden de
      arranque, qué pasa si se omite cada paso y demostración de punta a punta) y orden de arranque en los README
      de Airport e Itinerary Service.
    - Jobs de CI `send-notification-function` (pruebas y `docker build` de la imagen) y `event-trigger`;
      `serverless` en `sonar.sources` y `sonar.tests` (ADR-023).
    - Demostración real (2026-11-11): caso normal, duplicado, evento en la DLQ por la "migración faltante" (tabla
      renombrada) y su reprocesamiento, evento inválido y mensaje no JSON.
    - Totales: SendNotificationFunction **59 pasan** con PostgreSQL (**53 pasan, 6 omitidas** sin él); Event
      Trigger **84 pasan** con RabbitMQ y la función (**68 pasan, 16 omitidas** sin ellos); Itinerary Service
      **167 pasan** con servicios (**142 pasan, 25 omitidas** sin ellos).
  - Corrección del Quality Gate de SonarCloud en el PR #11 (commit `375fb26`): el único problema de Reliability
    (aserción con la misma expresión a ambos lados en `test_notification_record.py`) y 7 de Maintainability
    (`with` anidados, comillas en el `Dockerfile`, un solo llamado dentro de `pytest.raises`). Se mantienen 3
    `logger.error` donde SonarCloud sugiere `logging.exception()` (errores esperados: mensaje que no es JSON y
    RabbitMQ no disponible o que no acepta el mensaje en `replay_dlq`), con un comentario que explica el motivo.
    Además, el engine de la función usa `hide_parameters=True`: los errores de SQLAlchemy ya no llevan al log el
    correo ni el nombre del viajero. SendNotificationFunction: **60 pasan** con PostgreSQL.
- **Rama `fix/aislar-pruebas-itinerary`** (antes de la Fase 7), **fusionada en `main`** (PR #13, merge `825f1be`):
  - Commit `test:`: las pruebas de integración de Itinerary Service con RabbitMQ usan una topología propia
    (`IsolatedTopology`, prefijo `test-<id>.`) declarada una vez por sesión de pytest y borrada al terminar, como las
    del trigger en la 6C (fixtures `rabbitmq_parameters`, `isolated_topology`, `isolated_publisher` y
    `unbound_notification_queue`, que ahora desenlaza la cola de prueba). Ninguna prueba necesitó omitirse.
    Para publicar en el exchange de prueba, `RabbitMQEventPublisher` y `declare_exchange` aceptan un `exchange`
    opcional (por defecto `itinerary.events`; la aplicación no lo cambia).
  - Commit `fix:`: `hide_parameters=True` en el engine de Itinerary Service (como en la función). El texto que
    genera el propio PostgreSQL todavía puede citar un valor en errores de conversión de tipo; aquí es poco
    probable porque Pydantic y el dominio validan antes.
  - Commit `docs:`: el equipo trabaja también en **macOS (Apple Silicon)**: sección 4 con comandos para PowerShell,
    CMD y zsh, tabla de equivalencias (4.2) y variantes zsh en el README raíz, los README de los cuatro componentes y
    `CONTRIBUTING.md`. Nuevo pendiente en 9.3: las pruebas de integración siguen usando y borrando la base real
    `itinerary_db`.
  - Verificación (2026-11-11, en macOS): con 1 mensaje en `notification.itinerary-created` y 1 de prueba en su DLQ,
    `pytest` en Itinerary Service deja **los mismos conteos** (antes del cambio, la cola real quedaba en 0) y no deja
    colas ni exchanges `test-*`. Totales de Itinerary Service: **169 pasan** con PostgreSQL y RabbitMQ; **144 pasan,
    25 omitidas** sin ellos.
- **Fase 7 (API Gateway):** completada y **fusionada en `main`** (PR #14, merge `044fa80`) con la **etiqueta `fase-7`**.
  La rama `fase-7-api-gateway` se conserva como archivo de solo lectura. ADR-009 aceptada: Nginx (sección 9.1).
  - Entrega **7A** completada: carpeta `gateway/` con `Dockerfile` (`nginx:1.30.6-alpine`), `.dockerignore`,
    `templates/default.conf.template`, `.env.example` y README básico. `nginx -t` correcto. Demostración real
    (2026-11-11, macOS) con los servicios en uvicorn en `127.0.0.1` (Docker Desktop llega a ellos por
    `host.docker.internal`): enrutamiento de los dos servicios, errores de los servicios sin cambios (404, 422 y el 503
    de Itinerary con Airport apagado), 404 `ROUTE_NOT_FOUND`, 502 `UPSTREAM_UNAVAILABLE` con Airport apagado,
    `X-Correlation-ID` reenviado, generado y reemplazado si es inválido, y redirección de `/api/airports/` traducida
    por `proxy_redirect`. Con un servidor eco temporal (fuera del repositorio): `Authorization` y `X-Forwarded-*`
    llegan al servicio, 504 `UPSTREAM_TIMEOUT` con un timeout de 2 s, y un 502 generado por el servicio pasa sin cambios.
  - Entrega **7B** completada: rate limiting (`limit_req_zone` por IP, `location /api/` que agrupa las rutas de los
    servicios, variables `GATEWAY_RATE_LIMIT` y `GATEWAY_RATE_BURST`, 429 `RATE_LIMIT_EXCEEDED` con `Retry-After: 1`).
    Pruebas en `gateway/tests` (entorno virtual `gateway/.venv`, `requirements-dev.txt` con pytest y httpx): contenedores
    propios del gateway (`api-gateway:test`, puertos libres de 127.0.0.1, borrados al terminar) contra servidores eco de
    Python (`tests/echo_server.py`), y pruebas *smoke* solo `GET` contra el gateway real (`GATEWAY_URL`, omitidas si no
    corre). Hallazgo: en Docker Desktop, `--add-host=host.docker.internal:host-gateway` agrega una IPv6 inalcanzable y
    la mitad de las solicitudes daba 502, así que las pruebas solo lo usan en Linux (documentado en ADR-009 y en el README
    del gateway). Total: **40 pasan, 3 omitidas** sin el gateway real; **43 pasan** con él y los dos servicios (3
    ejecuciones seguidas estables, ~5 s, sin contenedores sobrantes). Tras la suite completa, el gateway real seguía
    aceptando 18 solicitudes seguidas (su límite no se tocó). Demostración real en zsh: 22 × 200 y luego 429. No
    verificado en Windows: si las pruebas de enrutamiento dan 502, `GATEWAY_TEST_ECHO_HOST=0.0.0.0`.
  - Entrega **7C** completada:
    - Documentación: `docs/01` (nombre de la fase), `docs/02` (2.5 "API Gateway" y tráfico norte-sur vs. este-oeste),
      `docs/04` (nueva sección 2.3), `docs/05` (gateway en los diagramas general, de componentes, de secuencia y de
      despliegue, y nuevo diagrama 3.2 con el recorrido de una solicitud por el gateway), ADR-012 y sección 10.2 con los
      errores del gateway, sección 10.1 con sus rutas. README raíz (alcance, tecnologías, diagrama, resumen de la Fase 7,
      paso 8 del orden de arranque, filas de "qué pasa si se omite", demostración de punta a punta por
      `http://localhost:8000/api/itineraries`) y paso 8 en el orden de arranque de los otros cuatro README.
    - CI: job `api-gateway` en `tests.yml` (construye la imagen, `nginx -t` con `--add-host` y `pytest -v`; en el
      runner las pruebas aisladas se ejecutan de verdad porque hay Docker; las *smoke* quedan SKIPPED). SonarCloud:
      `gateway` en `sonar.tests` (ADR-023). En el PR #14 pasaron todos los checks: el job "API Gateway" (las pruebas
      aisladas corrieron en el runner Linux, donde `--add-host` no causó el problema de IPv6) y SonarCloud.
    - Demostración real (2026-11-11, macOS) con los ocho pasos del orden de arranque: `POST /api/itineraries` por el
      gateway con `X-Correlation-ID: demo-e2e-gateway` → 201 → relay `2 publicados` → trigger `PROCESSED` → fila en
      `notification_history` con `correlation_id = demo-e2e-gateway`. Sin el header, el gateway generó
      `fa22cd0e-...` y ese mismo valor llegó al relay y al historial. CRUD por el gateway (GET, PUT, DELETE → 204, GET →
      404 `ITINERARY_NOT_FOUND`), 422 `AIRPORT_NOT_FOUND` del servicio sin cambios y `map-data` (51). Al arrancar,
      el trigger procesó un evento inválido de prueba que estaba en la cola real desde la verificación de
      `fix/aislar-pruebas-itinerary` (`event_id=c3d4e5f6-...`) y lo envió a la DLQ (comportamiento de ADR-031): la DLQ
      quedó con 2 mensajes de prueba.
    - Pruebas del gateway: **43 pasan** con el sistema completo encendido.
- **Fase 8 (Frontend):** completada y **fusionada en `main`** (PR #19, merge `0ea61fa`) con la **etiqueta `fase-8`**.
  La rama `fase-8-frontend` se conserva como archivo de solo lectura. ADR-033 aceptada (sección 9.1).
  - Entrega **8A** completada: infraestructura del frontend (`frontend/`, `index.html`, `css/style.css`, `js/api.js`,
    `js/main.js`); gateway actualizado para servir estáticos desde la raíz del repositorio (`Dockerfile` con contexto
    raíz, `Dockerfile.dockerignore`, `location / { try_files ... }`, `location @route_not_found` en JSON);
    `test_routing.py` actualizado; `test_static.py` nuevo (5 pruebas); CI actualizado.
  - Entrega **8B** completada: mapa de aeropuertos con Plotly 4.3.0 bundle parcial geo (`plotly-geo.min.js`, 1.4 MB,
    local); `scattergeo` centrado en Colombia (lat -5..13, lon -82..-65), un trazo por tipo de aeropuerto con colores
    propios; tooltip con nombre, IATA, ciudad, departamento; conteo real (51, no 52: el id 43 sin coordenadas).
  - Entrega **8C** completada: CRUD de itinerarios en `itineraries.js`; formulario de 2 columnas con desplegables de
    aeropuertos ordenados por ciudad; tabla con edición inline y eliminación con `confirm()`; `datetime-local` → ISO 8601
    con offset del navegador (ADR-017); todo texto de datos con `textContent`; errores con `correlation_id` y botón
    "Copiar" en 5xx; recarga de datos frescos al cambiar de pestaña.
  - Pruebas del gateway (Fase 8 fusionada): **48 recogidas** (no 43 como constaba en la Fase 7; las 5 de
    `test_static.py` se agregaron en la 8A). El PR #19 se fusionó con el check "API Gateway" fallando:
    `test_nonexistent_file_returns_route_not_found_json` devolvía `text/html` en lugar de `application/json`
    porque Nginx resuelve el `Content-Type` por la extensión de la URI (`.html` → mime.types) antes de aplicar
    `default_type`. Corregido en la rama `fix/gateway-404-json` con `types { }` vacío en las seis ubicaciones
    que devuelven JSON de error (ver sección 9.1 ADR-033 y el PR de corrección). Total tras el fix:
    **48 pasan, 3 omitidas** (smoke, sin el gateway real).
- **Fase 9 (Observabilidad):** completada y **fusionada en `main`** (PR #21, merge `d9ed023`) con la **etiqueta `fase-9`** sobre ese commit. La rama `fase-9-observabilidad` se conserva como archivo de solo lectura.
  - Entrega **9A** completada: ADR-034 a ADR-036. Logs JSON estructurados con `python-json-logger==4.2.0` en los cuatro
    componentes Python: `configure_logging(log_level, service_name)` en `app/logging_config.py`; `JsonFormatter` con campos
    `timestamp`, `level`, `service`, `correlation_id`, `trace_id`, `span_id`, `logger`, `message`; `CorrelationIdFilter`
    y `OTelContextFilter` que leen `ContextVar` del request; pruebas de `test_logging_config.py` en Airport e Itinerary
    Service. `LOGGING` confirmado en `docs/06-decisiones-arquitectonicas.md` (ADR-034).
  - Entrega **9B** completada (commit `7dd9087`): ADR-035. Trazas distribuidas con `opentelemetry-sdk==1.45.2` y
    exportador OTLP gRPC a Jaeger 2.23.0 (ADR-039). `setup_tracing(service_name)` en cada componente: modo prueba
    (`InMemorySpanExporter`+`SimpleSpanProcessor`) vs. producción (`OTLPSpanExporter`+`BatchSpanProcessor`). Gateway con
    imagen `nginx:1.30.6-alpine-otel`, variable `GATEWAY_OTEL_TRACE`. Propagación W3C por toda la cadena: Outbox escribe
    `traceparent` en la columna de la outbox (migración `e6f0a4b8c1d9`); relay lo restaura antes de publicar en
    RabbitMQ; consumer del trigger lo extrae de los headers AMQP; lambda invoker lo inyecta en el cuerpo del evento;
    handler de la función lo restaura. 4 pruebas nuevas (2 en `test_outbox_event_publisher.py`, 2 en
    `test_outbox_relay.py`).
  - Entrega **9C** completada: ADR-038. Métricas Prometheus con `prometheus-client==0.21.1`. Airport e Itinerary Service:
    middleware HTTP `metrics_middleware` (recuento y duración por `method`, `path` como plantilla de ruta, `status`),
    endpoint `/metrics` con `make_asgi_app()`. Itinerary Service: contador de negocio `itineraries_created_total`
    incrementado en `create_itinerary()`. Outbox Relay (puerto 9101): `start_http_server()`; contadores
    `outbox_events_published_total`, `outbox_events_failed_total`, `outbox_events_dead_total`, `outbox_relay_cycles_total`.
    Event Trigger (puerto 9102): `start_http_server()`; contador `notifications_dispatched_total{outcome}` en
    `DeliveryHandler`. Variables `.env.example`: `OUTBOX_RELAY_METRICS_PORT=9101` y `METRICS_PORT=9102`. Configuración de
    observabilidad en `observability/`: `prometheus/prometheus.yml` (4 targets), Grafana 11.3.1 con provisioning de
    datasource y dashboard `sistema-itinerarios.json` (paneles de negocio, HTTP req/s y latencia p50/p95/p99, relay y
    trigger). 10 pruebas nuevas (4 en Airport, 6 en Itinerary). Totales: Airport **201 pasan**; Itinerary **163 pasan,
    25 omitidas**; Event Trigger **70 pasan, 16 omitidas**.
  - Entrega **9D** completada: documentación de la Fase 9. `docs/02` sección 6 reemplazada con la implementación
    concreta (logs JSON, trazas W3C con Jaeger, métricas con Prometheus y Grafana). `docs/05` diagrama de despliegue
    actualizado con los componentes reales de observabilidad (Jaeger :16686, Prometheus :9090, Grafana :3000) y nuevo
    diagrama 5.1 del flujo de datos de observabilidad. `docs/06` con ADR-033 a ADR-039. `README.md` raíz: tabla de
    estado, nuevo paso 2 "Observabilidad" en el orden de arranque (Jaeger, Prometheus y Grafana), sección "Fase 9 —
    Observabilidad" y sección "Demostración de observabilidad", rama `fase-8-frontend` en la tabla de ramas.
    READMEs de los cuatro componentes actualizados con sección "Observabilidad (Fase 9)".
  - **Cierre de la Fase 9** (rama `docs/cierre-fase-9`): dos correcciones que quedaron fuera de la entrega 9D:
    - Commit `af6cf61` — `refactor: extrae logging, trazas y métricas HTTP a libs/observability (Microservice Chassis
      Pattern)`: SonarCloud detectó 25,3 % de duplicación por los cuatro `logging_config.py`/`tracing.py` idénticos.
      Se crea `libs/observability` (ADR-040) con los tres módulos compartidos; los cuatro componentes actualizan sus
      importaciones y `requirements.txt`; el Dockerfile de SendNotificationFunction cambia el contexto de build a la
      raíz; `sonar.sources` incluye `libs`. 32 archivos cambiados.
    - Commit `1e0681b` — `fix: corrige carga del módulo OTel y propagación de traceparent en el gateway`: el CI del
      gateway fallaba con `unknown directive "otel_exporter"` porque `load_module` no estaba en ningún `nginx.conf`
      principal. Se crea `gateway/nginx.conf` con `load_module modules/ngx_otel_module.so;` y se copia en el
      Dockerfile. Se elimina `proxy_set_header traceparent/tracestate` del template (sobrescribía el span hijo que
      inyecta `otel_trace_context propagate`). 2 pruebas nuevas de propagación de `traceparent`.
      Gateway: **50 pasan, 3 omitidas** (smoke, sin el gateway real).
    - `docs/06` ampliado con ADR-036 (corrección) y ADR-040 (nuevo). `CLAUDE.md` sección 6, 7.5, 9.1 y 15
      actualizados. READMEs con nota sobre `libs/observability`.
- **Fase 10 (Docker y Docker Compose):** completada y **fusionada en `main`** (PR #23, merge `58d16e6`) con la
  **etiqueta `fase-10`** (creada en el cierre de la Fase 11). La rama `fase-10-docker-compose` se conserva como archivo de solo lectura. ADR-041 aceptada
  (sección 9.1).
  - Entrega **10A**: Dockerfiles de Airport Service, Itinerary Service (una imagen para la API, el relay y las
    migraciones), Event Trigger y `Dockerfile.migrations` de la función, con `Dockerfile.dockerignore` por imagen.
    Se agregó también el de la imagen de la función: desde la Fase 9 su build enviaba todo el repositorio.
  - Entrega **10B**: `docker-compose.yml` (15 servicios), `observability/prometheus/prometheus.compose.yml` y
    `.env.example` en la raíz. Corrige dos detalles del modo manual de la Fase 9 que solo funcionan en una red
    Docker: el datasource de Grafana (`prometheus:9090`) y el montaje de los dashboards en `/var/lib/grafana/dashboards`;
    además, las trazas de la función ahora llegan a Jaeger (`OTEL_EXPORTER_OTLP_ENDPOINT`).
  - Entrega **10C**: ADR-041 en `docs/06`, `docs/02` sección 7, `docs/05` (diagrama de despliegue con redes y orden de
    arranque), README raíz (arranque con Compose como forma recomendada, arranque manual como modo de desarrollo,
    equivalencias de comandos en las demostraciones, ramas `fase-9` y `fase-10`), README de los cinco componentes y
    job de CI "Docker Compose" (validar, construir, levantar, comprobar migraciones, colas, métricas, 422 por el
    gateway y aislamiento de redes; sin llamar a API Colombia).
  - Validación: el equipo donde se escribió la fase **no tenía Docker**; `docker-compose.yml` y el workflow se
    validaron con un script (YAML, dependencias, redes, Dockerfiles, montajes y puertos). La verificación con
    `docker compose up` queda para el equipo y para el job de CI del PR.
- **Rama `fix/sonarcloud-dockerfiles`** (después de la Fase 10): el Quality Gate de SonarCloud falló en `main` con
  8 vulnerabilidades (calificación de seguridad C) en los cuatro Dockerfiles nuevos, todas en su `pip install -r`:
  regla S8541 (falta `--only-binary :all:`, pip podría ejecutar scripts de instalación) y S8544 (dependencias sin
  versión fija: la línea `-e ../../libs/observability`). Corrección: `requirements-runtime.txt` en Airport, Itinerary
  y el trigger (solo dependencias de ejecución con `==`; `requirements.txt` lo incluye con `-r` y añade
  `libs/observability`, `pytest` y `respx`, así que los comandos de instalación no cambian), `requirements-migrations.txt`
  en la función (incluido por `requirements-dev.txt`), `pip install --only-binary :all:` en los cuatro Dockerfiles y
  `libs/observability` por `PYTHONPATH` en las imágenes. Se resuelve también el pendiente de `pytest` y `respx` dentro
  de las imágenes. Antes del cambio se comprobó que todas las dependencias publican *wheels* para Linux.
- **Rama `fix/sonarcloud-require-hashes`**: tras el PR #24 SonarCloud mantenía 4 vulnerabilidades S8544 (una por
  Dockerfile, en su `pip install`): fijar con `==` las dependencias directas no basta, porque las transitivas se
  resolvían en cada build y nada verificaba los archivos descargados. Corrección: un `requirements-lock.txt` por
  imagen con todas las dependencias (directas y transitivas), versión exacta y hashes SHA-256 de sus *wheels* Linux
  (x86_64 y aarch64), instalado con `pip install --only-binary :all: --require-hashes`. Se genera con
  `python scripts/lock_requirements.py` (nueva carpeta `scripts/`, aprobada por el usuario; resuelve dentro de
  `python:3.12-slim` en amd64 y arm64 y toma los hashes de PyPI) a partir de `requirements-runtime.txt` /
  `requirements-migrations.txt`, que siguen siendo los archivos que edita el equipo. El job "Docker Compose" ejecuta
  `python3 scripts/lock_requirements.py --check`. ADR-041 actualizada. La imagen de la función (`Dockerfile`, base de
  AWS Lambda) no tenía la alerta y no cambia.
- **Fase 11 (Pruebas):** completada y **fusionada en `main`** (PR #26, merge `9261cc4`) con la **etiqueta `fase-11`**.
  La rama `fase-11-pruebas` se conserva como archivo de solo lectura. ADR-042 aceptada (sección 9.1). Antes de empezar:
  PR #25 (`fix/sonarcloud-require-hashes`) fusionado; SonarCloud en `main` con Quality Gate OK, seguridad A y 0
  vulnerabilidades. La 11A cerró además el pendiente de que las pruebas de integración usaban y borraban las bases
  reales (`itinerary_db`, `notification_db`).
  - Entrega **11A** (commit `381b1b9`): bases `itinerary_db_test` y `notification_db_test` creadas y migradas por las
    pruebas; la prueba del handler de Lambda apunta a la base de pruebas (antes usaba la real; ahora tarda 6 s en lugar
    de 91 s porque no intenta exportar trazas). `libs/observability`: 18 pruebas, `requirements-dev.txt`, job de CI.
    Gateway: en Windows 11 `host.docker.internal` resolvía también a IPv6 y la mitad de las pruebas de enrutamiento
    daba 502; las pruebas lo fijan a IPv4. En la 11D, con el equipo cargado, falló a veces
    `test_limit_applies_to_both_services` (exigía 429 en la primera solicitud tras agotar el límite, pero a 10 r/s se
    libera una cada 100 ms): ahora exige un 429 entre las 5 siguientes, que sigue probando que el límite es por IP.
  - Entrega **11B** (commit `0c33b2a`): contrato HTTP `docs/openapi/airport-service.json` (Airport proveedor,
    Itinerary consumidor) y contrato del evento en la función (`pyyaml==6.0.3` en su `requirements-dev.txt`).
  - Entrega **11C** (commit `1e8cf79`): `docker-compose.e2e.yml`, `tests/e2e` (14 pruebas) y su paso en el CI. Hallazgo:
    `docker compose up --build` construyó tres veces en paralelo la imagen compartida de Itinerary Service y una falló
    con `image ... already exists`; `docker compose build` y luego `up` (lo que hace el CI) funciona.
  - Entrega **11D**: filtros de advertencias, ADR-042, README raíz (sección "Pruebas"), README de Airport, Itinerary,
    función y gateway, y este estado.
  - Verificación (2026-11-18, Windows 11, sistema completo con el simulador): libs/observability 18, Airport 203,
    Itinerary 195, función 70, Event Trigger 86, gateway 53 y E2E 14: **639 pasan, 0 fallos, 0 omitidas, 0
    advertencias**. Sin servicios: Itinerary 170 pasan y 25 omitidas; función 64 pasan y 6 omitidas.
- **Cierre de la Fase 11** (rama `docs/cierre-fase-11`, 2026-11-18):
  - Etiquetas anotadas `fase-10` (sobre `58d16e6`) y `fase-11` (sobre `9261cc4`) creadas y subidas.
  - Ramas auxiliares ya fusionadas borradas en GitHub: `docs/cierre-fase-9`, `fix/gateway-404-json`,
    `fix/sonarcloud-dockerfiles` y `fix/sonarcloud-require-hashes`. Las ramas `fase-*` se conservan.
  - Decisiones de la 9.3 resueltas: se mantiene la limitación de la IP de los servicios en el gateway con Compose
    (ADR-041) y se borró `serverless/send-notification-function/.dockerignore` (sin efecto desde la Fase 9).
    `GenerateItineraryReportFunction` no se implementa por alcance (ADR-043). La 9.3 queda solo con la protección
    de `main`, que configura el dueño del repositorio en GitHub.
  - Fusionado en `main` (PR #27, merge `6078e16`). Quedó una lista de pendientes de las Fases 0 a 11: los grupos A
    (configuración y pruebas) y B (documentos que contradicen el código) se corrigen antes de la Fase 12; los grupos
    C (estados de ADR) y D (CLAUDE.md 7.5, 7.6 y 12, resúmenes del README) quedan para la Fase 12.
- **Rama `fix/limpieza-config`** (grupo A, configuración y pruebas):
  - Contexto de build de la imagen de SendNotificationFunction: su Dockerfile hace `COPY libs/` y el
    `Dockerfile.dockerignore` dejaba pasar todo `libs/observability/`. Con `libs/observability/.venv` presente
    (ADR-042 indica crearlo para sus pruebas), la imagen llevaba 73 MB de más (`.venv`, `tests/`). Ahora solo pasan
    `pyproject.toml` y `observability/**`: contexto de 70 MB a 46 KB, `libs/` en la imagen de 73 MB a 92 KB.
  - Gateway: `Dockerfile.dockerignore` con lista blanca exacta (`nginx.conf`, `templates/`, `frontend/`) en lugar de
    `!gateway/`, que volvía a incluir toda la carpeta. En el build real no tenía efecto (BuildKit solo transfiere lo
    que nombran los `COPY`: 1,46 MB antes y después); se mantiene como prevención. Se borró `gateway/.dockerignore`,
    sin efecto desde la Fase 8 (contexto en la raíz).
  - `.env.example`: `SERVICE_NAME` en el del trigger; `OTEL_ENABLED` y `OTEL_EXPORTER_OTLP_ENDPOINT` comentadas en
    los cuatro componentes Python, con la aclaración de que OpenTelemetry las lee del entorno del proceso y no del
    `.env` (escribirlas ahí no tiene efecto).
  - Pruebas: se borraron `tests/test_logging_config.py` y `tests/test_tracing.py` de Airport e Itinerary Service
    (21 pruebas que solo probaban `libs/observability` con un nombre de servicio escrito a mano). La única sin
    equivalente (log dentro de un span → línea JSON con `trace_id` y `span_id`) pasó a
    `libs/observability/tests/test_logging_config.py`.
  - Verificación (2026-11-18, macOS, sin servicios encendidos): libs/observability **19**, Airport **191**, Itinerary
    **161 pasan, 25 omitidas**, Event Trigger **70 pasan, 16 omitidas**, función **64 pasan, 6 omitidas**, gateway
    **50 pasan, 3 omitidas**; `docker compose build` de las seis imágenes, `docker compose config` (con y sin
    `docker-compose.e2e.yml`) y `nginx -t` correctos. Los entornos virtuales de este equipo estaban desactualizados
    (anteriores a la Fase 9) y se reinstalaron con `pip install -r`.
  - Fusionada en `main` (PR #28, merge `d94a2e4`).
- **Rama `docs/correcciones-documentacion`** (grupo A de texto y grupo B, solo documentación):
  - AsyncAPI 1.2.0: header AMQP `traceparent` documentado como opcional (`event_version` sigue obligatorio); el
    payload y la `event_version` del evento no cambian.
  - README raíz: carácter de control (BEL) en `.venv\Scripts\activate` de las pruebas E2E. CLAUDE.md sección 6:
    `pyyaml==6.0.3` (prueba de contrato de la función).
  - ADR desactualizados: notas `*Actualización (Fase N, ADR-X):*` sin reescribir lo decidido (ADR-009, 016, 029,
    034, 035, 036, 038 y 039); nombre `OTelContextFilter` corregido en ADR-040 y en esta sección.
  - Documentos alineados con el código: imagen `nginx:1.30.6-alpine-otel` (README raíz y del gateway, fila de
    ADR-009), `libs/observability` en lugar de `app/logging_config.py` y `app/tracing.py` (docs/02 y README de los
    componentes), `notification-data` en Compose (fila de ADR-029, `.env.example` de la función), textos en futuro
    o preliminares ya cumplidos (docs/01 a docs/05, README del gateway), 7.4 con `OutboxEventPublisher` y 10.1 con los
    504 de Airport (ADR-014) e Itinerary (ADR-019).
  - Se mantuvo sin cambios la lista de criterios de la Fase 0 en `docs/01` (sección 9): describe cómo se aprobó esa
    fase. Los grupos C y D quedan para la Fase 12.
  - Verificación: pruebas que comparan el AsyncAPI con el código (Itinerary 5, función 10, trigger 6) pasan; ningún
    archivo del repositorio tiene caracteres de control.
- **Fase 12 (Documentación y entrega):** completada y **fusionada en `main`** (PR #30, merge `aee3726`) con la
  **etiqueta `fase-12`** sobre ese commit (plan en la sección 12.12). La rama `fase-12-documentacion` se conserva como
  archivo de solo lectura.
  - Entrega **12A**: `docs/05` con diagramas de clases (sección 3: Airport con los roles del Adapter y los
    Decorators, Itinerary API, Outbox Relay y función) y relacional (sección 4: `itinerary_db` y `notification_db`,
    índices, restricciones y referencias entre bases), índice al inicio y secciones renumeradas (secuencia 5,
    resiliencia 6, despliegue 7). Del README raíz salieron, sin cambios de fondo: el arranque manual y "Qué pasa si se
    omite un paso" a `docs/07-ejecucion-manual.md`; las demostraciones de punta a punta y de observabilidad a
    `docs/08-demostraciones.md`; los resúmenes "Fase 2" a "Fase 11" a `docs/10-historial-de-fases.md`. El README
    queda con el contenido existente en el nuevo orden (descripción, arquitectura, instalación y ejecución, pruebas,
    documentación adicional, desarrollo por fases, Claude Code y contexto académico con los datos del equipo).
    Enlaces actualizados en `docs/02`, `docs/05` y los README de Airport, Itinerary, la función y el trigger.
    Comprobado: los 15 diagramas de `docs/05` se dibujan sin errores con Mermaid 11.
    Commits `db4cd63` (diagramas) y `f026efc` (reorganización).
  - Entrega **12B**:
    - README completo: inicio rápido; "Arquitectura" con un apartado corto por concepto (qué es y por qué, dónde
      está en el código, enlace a `docs/`); diagramas general, de secuencia, relacional y de despliegue (copias de
      `docs/05`, que lo indica en "Consideraciones"); variables de entorno de Compose y de cada componente; endpoints
      por el gateway con sus códigos de error; contrato y topología del evento; pruebas con los totales ejecutados;
      limitaciones conocidas (ADR-008, ADR-041, ADR-043 y protección de `main`); tabla de los 43 ADR; estructura del
      repositorio.
    - Totales confirmados ejecutando las siete suites (2026-11-18, macOS, Compose con el simulador): libs/observability
      19, Airport 191, Itinerary 186, función 70, Event Trigger 86, gateway 53 y E2E 14: **619 pasan, 0 fallos, 0
      omitidas, 0 advertencias**.
    - Contradicciones corregidas (documentación contra código): totales de pruebas (README, ADR-042, `docs/10`, README
      de Airport e Itinerary); `prometheus.yml` en el resumen de la Fase 9; verbos en futuro en "Alcance", `docs/02`,
      `docs/03`, `docs/04`, `docs/05` y `docs/08`; definición de Adapter invertida y `Airport` sin atributos en
      `docs/03`; paneles y ruta del dashboard de Grafana en `docs/02`; referencia a la sección 3.2 de `docs/05` (ahora
      5.2) en `docs/04`; `AirportNotFoundError` en ADR-019 (en el código, `AirportNotFoundInCatalogError`);
      `opentelemetry-propagator-b3` en ADR-035 (no se instala; se usa el propagador W3C por defecto); 422 de
      `GET`/`DELETE /itineraries/{id}` con un id que no es UUID (sección 10.1); comentario de `docker-compose.yml`
      que remitía al README. Dos errores reales de documentación: el diagrama de topología de RabbitMQ de `docs/04`
      no se dibujaba (etiqueta con puntos en la flecha), y los comandos manuales de Prometheus y Grafana de `docs/07`
      dejaban Grafana sin dashboard y con el datasource roto (faltaban la red `observability-net` y el montaje de
      `dashboards/`; también faltaba la variante de PowerShell). Los comandos corregidos se probaron en macOS; la
      variante de PowerShell no se probó en Windows.
    - Grupo C (`docs/06`): estados de ADR-001 a ADR-006 y ADR-010 (aceptadas en la Fase 0 e implementadas en la fase
      que se indica), ADR-012 (504 y `/metrics`), ADR-025 (implementada; condición con `failed_at`), ADR-033 con
      contexto, decisión, justificación y consecuencias, nota de totales en ADR-042 y sección 2 "Revisión y
      mantenimiento de las decisiones".
    - Grupo D (este archivo): filas de ADR-034, 035, 037, 038 y 039 en la 9.1; 7.5 con `docs/07`, `08` y `10`; 7.6 con
      el puerto 4317; 10.1 con los 422; sección 12 con la columna de estado (la Fase 0 no tiene etiqueta), el plan de
      la Fase 9 (12.9, reconstruido a partir de esta sección), planes renumerados (Fase 12 → 12.12), sin el `---`
      suelto y sin Testcontainers en la Fase 11.
    - Verificado: ningún enlace interno roto y los 30 diagramas Mermaid del repositorio se dibujan sin errores con
      Mermaid 11.
  - Commits de la 12B: `366922e`, `1abcd96` y `91b99a3`.
  - Entrega **12C**:
    - Evidencias en `docs/evidencias/` (índice en su `README.md`, sección "Evidencias" del README raíz): 01 a 07 en
      texto (`scripts/evidencias_terminal.py`: pruebas, `docker compose ps`, correlation ID, 429, `notification_history`,
      Outbox con RabbitMQ detenido, evento inválido en la DLQ) y 08 a 18 en PNG (`scripts/capturar_evidencias.py`, con
      `playwright==1.64.1` aprobado por el usuario en `scripts/.venv`: Swagger, mapa, CRUD paso a paso, Jaeger, Grafana,
      RabbitMQ). Una sola sesión el 2026-11-18 en macOS, con la API Colombia real (el simulador solo para las E2E de la
      01). 19 (SonarCloud) y 20 (GitHub Actions) quedan reservadas para el equipo.
    - Dos errores reales encontrados al capturar, corregidos con aprobación del usuario:
      1. **Event Trigger:** tras perder la conexión con RabbitMQ, el span del último mensaje quedaba activo y un mensaje
         posterior sin `traceparent` aparecía en Jaeger como hijo de una traza ajena. `RabbitMQConsumer.run` procesa
         cada conexión en una copia del contexto (`contextvars`); prueba nueva (falla sin la corrección); nota en ADR-037.
         Comprobado en el sistema real. Event Trigger: **87** pruebas; total **620**.
      2. **Grafana:** el panel "Mensajes en DLQ" consultaba `outbox_events_dead_total` (mensajes venenosos de la outbox);
         ahora cuenta lo que el Event Trigger envió a la DLQ (`notifications_dispatched_total` con `rejected` o
         `function_error`). Nota en ADR-038.
    - Hueco de documentación corregido: para volver del simulador a la API real hay que reiniciar el gateway (ADR-041) y
      vaciar la caché de Redis (si no, el mapa muestra los 4 aeropuertos del simulador). README ("Pruebas"),
      `docs/evidencias/README.md` y la guía lo indican.
    - `docs/09-guia-sustentacion.md`: preparación (qué levantar, comprobaciones, plan B con el simulador o las
      evidencias), guion de 11 pasos con tiempos (unos 25 min), reparto sugerido entre los tres integrantes, 10 preguntas
      probables y otras tres, y cómo explicar las limitaciones conocidas.
    - Revisión final: enlaces internos y anclas sin errores, ningún verbo en futuro sobre algo ya construido (quedan los
      de `docs/01`, que es la planificación original, y la nota histórica de `docs/03`), orden de lectura del README
      (descripción → inicio rápido → arquitectura → diagramas → ejecución → referencia → evidencias → limitaciones → ADR).
    - Datos de ejemplo creados en la sesión: itinerarios de "Ana Pérez" y "Luis Gómez" (`@example.com`) y sus
      notificaciones; el mensaje de demostración en la DLQ. Los de las sesiones descartadas se borraron por la API.
- **Fase 12:** completada y **fusionada en `main`** (PR #30, merge `aee3726`) con la **etiqueta `fase-12`**. La rama
  `fase-12-documentacion` se conserva como archivo de solo lectura. Las evidencias 19 (SonarCloud) y 20 (GitHub
  Actions) las agregó el equipo después (ver más abajo).
- **Rama `fix/commit-antes-de-responder`** (después de la Fase 12): el job "Docker Compose" falló de forma
  intermitente en la E2E `test_crud_completo_por_el_gateway` (DELETE → 204 y el GET inmediato → 200 en lugar de 404).
  - Causa: `get_db_session` hacía `session.commit()` después del `yield`, y en FastAPI 0.162 ese código (alcance
    `"request"`, el de por defecto) corre **después de enviar la respuesta** (`fastapi/routing.py`: la pila de salida
    de la solicitud se cierra tras `await response(...)`). PUT y DELETE respondían antes de confirmar; POST no tenía el
    problema porque `CreateItineraryUseCase` ya confirmaba con `UnitOfWork`.
  - Corrección (nota en ADR-019): `UpdateItineraryUseCase` y `DeleteItineraryUseCase` reciben `UnitOfWork` y confirman
    antes de devolver el resultado; las rutas PUT y DELETE inyectan `get_unit_of_work`; `get_db_session` ya no hace
    commit (solo rollback si hay excepción y `close`), así una escritura que olvide el commit pierde sus cambios
    siempre en lugar de depender de la velocidad. Diagrama de clases de `docs/05` actualizado. Se descartó
    `Depends(..., scope="function")` porque deja en la capa API la decisión de cuándo confirmar.
  - Ningún otro componente dependía de un commit en una dependencia con `yield`: Airport Service, el trigger y el
    gateway no tienen base relacional, y la función y el Outbox Relay confirman con su `UnitOfWork`.
  - Pruebas: `tests/api/test_commit_before_response.py` (5; compara el orden `commit` / `response_start` con una sesión
    que registra las operaciones y un middleware ASGI; con el código anterior fallaban 2 siempre) y
    `tests/application/test_update_delete_use_cases.py` (5). Itinerary Service: **196 pasan** con PostgreSQL y
    RabbitMQ. E2E (Compose con el simulador, 2026-11-18, macOS): 14 pasan en 5 ejecuciones seguidas y
    `test_crud_completo_por_el_gateway` pasa 30 de 30 (con 2 s entre ejecuciones: sin pausa, el rate limiting del
    gateway responde 429).
  - Fusionada en `main` (PR #32, merge `1e44260`).
- **Rama `docs/evidencia-github-actions`** (PR #31): el equipo subió desde GitHub `docs/evidencias/20-github-actions.png`
  (los 8 checks del PR #30 de la Fase 12 en verde: los 7 jobs del workflow "Pruebas" y SonarCloud con "Quality Gate
  passed"). La rama se actualizó con un merge de `origin/main` (sin conflictos) para traer la corrección del PR #32. La
  evidencia 20 queda enlazada y sin la marca "Pendiente" en `docs/evidencias/README.md` y en la sección "Evidencias"
  del README raíz. La evidencia 19 (SonarCloud) sigue pendiente hasta la rama `fix/sonarcloud-fiabilidad`.
  Fusionada en `main` (PR #31, merge `68408c4`).
- **Rama `fix/sonarcloud-fiabilidad`** (2026-11-19): SonarCloud sobre `main` mostraba fiabilidad C con 9 problemas
  abiertos en el código completo (el Quality Gate pasaba porque eran antiguos), todos en Airport Service. Ninguno se
  marcó como aceptado en SonarCloud; los 35 de mantenibilidad no se tocaron.
  - S9152 (`app/main.py`, `lifespan`): **real**. `await redis.aclose()` iba después del `async with`, así que una
    excepción durante el `yield` dejaba la conexión con Redis sin cerrar. Ahora va en un `finally`. Prueba nueva que
    fallaba antes de la corrección (`test_lifespan_closes_redis_even_if_shutdown_is_interrupted`).
  - S7503 ×7 (`app/api/errors.py`): **real, menor**: los siete manejadores de errores eran `async def` sin ningún
    `await`. Pasan a `def` (Starlette acepta los dos tipos y ejecuta los `def` en el threadpool), como recomienda la regla.
    Respuestas sin cambios. Al pasar a un hilo, `logger.exception` ya no encontraba la excepción en curso y el log del
    500 perdía el traceback (lo detectó una prueba nueva): `_unexpected_error` pasa `exc_info=error`.
  - S5863 (`tests/domain/test_coordinates.py`): **falso positivo** (comparaba dos instancias distintas con los mismos
    valores, no la misma expresión). Reescrita con dos variables y `assert first is not second`, para que se lea qué
    prueba: igualdad de objeto de valor.
  - Pruebas: `tests/api/test_error_handlers.py` (3) y 2 del `lifespan` en `tests/api/test_main.py`. Airport Service:
    **196 pasan** (con Redis). Verificado en Docker Compose con la API real: 200, 404 `AIRPORT_NOT_FOUND`, 422,
    `map-data` y parada limpia del contenedor.
  - Hallazgo corregido en la misma rama (no era de SonarCloud ni lo causó la rama): el log `ERROR` de un 500 salía con
    `correlation_id` vacío en Airport **e** Itinerary Service, aunque la respuesta sí lo llevaba. Causa (comprobada con
    la pila de middlewares): el 500 lo atiende `ServerErrorMiddleware`, la capa más externa, y el middleware de
    correlation ID corre dentro de `metrics_middleware` (`BaseHTTPMiddleware`), que ejecuta las capas internas en otra
    tarea con una copia del contexto: el `ContextVar` fijado allí no se ve afuera. El `trace_id` sí aparecía (lo abre la
    instrumentación de OpenTelemetry, más externa). Corrección: el manejador del 500 pasa
    `extra={"correlation_id": ...}` tomado de `request.state` (`CorrelationIdFilter` respeta el valor si ya viene).
    En Airport, `get_correlation_id` guarda en `request.state` el ID que genera, para que el log y la respuesta usen el
    mismo. En Itinerary, `_cid` del manejador de errores leía el header o generaba un UUID nuevo: sin header, el cuerpo de
    un error y el header de la respuesta traían IDs distintos, y con un header de más de 128 caracteres el cuerpo lo
    devolvía sin recortar. Ahora usa `request.state` como Airport (por el gateway no ocurría: siempre envía un ID válido).
    No se reordenaron los middlewares ni se cambió `libs/observability`. Pruebas: 3 más en
    `test_error_handlers.py` de Airport (**198 pasan**; *corrección en `docs/cierre-final`:* son **199**, porque la rama
    agregó 2 + 3 + 3 pruebas a las 191) y `tests/api/test_error_log_correlation.py` en Itinerary (4,
    fallaban antes de la corrección; **200 pasan**). Verificado en Compose: con `itinerary-postgres` detenido, `GET
    /api/itineraries` con `X-Correlation-ID: demo-500-log` → 500 y log JSON `ERROR` con ese `correlation_id`, `trace_id`
    y traceback; 422 directo sin header con el mismo ID en cuerpo y header; E2E 14 pasan dos veces.
  - Fusionada en `main` (PR #33, merge `baaf05a`). El análisis de SonarCloud de ese commit sobre `main` (*Overall
    Code*) quedó con Quality Gate aprobado, seguridad **A** (0 problemas), **fiabilidad A (0 problemas, antes C con 9)**,
    mantenibilidad A (32 problemas; antes 35, sin haberlos tocado a propósito), 0 problemas aceptados y 2,2 % de
    duplicación.
- **Evidencia 19 de SonarCloud:** el equipo subió la captura de ese análisis desde GitHub (PR #34, merge `ba95cae`), pero
  en `docs/19-sonarcloud.png`. La rama `docs/enlaza-evidencia-19` la mueve con `git mv` a
  `docs/evidencias/19-sonarcloud.png` (aprobado por el usuario), la enlaza sin la marca "Pendiente" en
  `docs/evidencias/README.md` y en la sección "Evidencias" del README raíz, enlaza las evidencias 19 y 20 en el paso 10
  de `docs/09-guia-sustentacion.md` y actualiza la sección 7.5 (evidencias 01 a 20). **Las 20 evidencias están
  completas.** Fusionada en `main` (PR #35, merge `d0ccc3b`).
- **Rama `docs/cierre-final`** (2026-11-19, solo documentación): alinea la documentación con lo que entró después de la
  Fase 12 (PR #32, #33, #34 y #35).
  - Estado de la Fase 12: fusionada con la etiqueta `fase-12` en el README raíz ("Estado de las fases" y "Ramas del
    repositorio") y en esta sección; `docs/10` cita las etiquetas `fase-1` a `fase-12`; la entrada de la evidencia 19
    indica su merge.
  - Totales confirmados ejecutando las siete suites (2026-11-19, macOS, Compose con el simulador e imágenes
    reconstruidas desde `main`): libs/observability 19, Airport **199**, Itinerary **200**, función 70, Event Trigger
    87, gateway 53 y E2E 14: **642 pasan, 0 fallos, 0 omitidas, 0 advertencias**. Sin servicios, Itinerary da 175 pasan
    y 25 omitidas. Airport da 199 y no 198 como se había registrado en `fix/sonarcloud-fiabilidad` (error al sumar; el
    código no cambió). Actualizados en el README raíz ("Pruebas" y "Evidencias"), los README de Airport e Itinerary,
    una nota nueva en ADR-042, `docs/09` (paso 10) y `docs/10`.
  - Evidencia 01 regenerada con `scripts/evidencias_terminal.py pruebas`; su fila y su fecha en
    `docs/evidencias/README.md`.
  - `docs/10-historial-de-fases.md`: sección "Correcciones posteriores a la Fase 12" (`fix/commit-antes-de-responder` y
    `fix/sonarcloud-fiabilidad`). `docs/09-guia-sustentacion.md`: pregunta 11, el commit después de responder como
    error real de consistencia encontrado por una prueba E2E.
  - La sección 9.3 (protección de `main`) no cambia hasta que el dueño del repositorio la configure.
- **Rama `feat/mejora-frontend`** (2026-11-23): mejora del frontend en tres entregas, un commit por entrega. Sigue siendo
  HTML, CSS y JavaScript sin framework, sin build y sin CDN, y solo habla con el gateway; no cambió la API, los servicios
  ni la configuración del gateway (nota en ADR-033).
  - Entrega 1 (`f19107b`): paleta de «carta aeronáutica» en variables CSS, **tema claro y oscuro** (sigue al sistema;
    el botón de la cabecera lo fija y lo guarda en `localStorage` con `try/catch`; el mapa de Plotly se redibuja con los
    colores del tema), **fuente D-DIN** (SIL OFL 1.1, de Datto) en `frontend/fonts/` con su licencia, tarjetas, botones
    con estados, pie con el curso y el equipo, y diseño para 375, 768 y 1280 px. Contraste WCAG AA calculado en los dos
    temas. `*.woff2 binary` en `.gitattributes`.
  - Entrega 2 (`001f59d`): `js/ui.js` (avisos y `<dialog>`), `js/route.js`, barra de carga, validación en el navegador
    con las reglas de ADR-015 (la fecha futura solo al crear: al editar un viaje ya pasado se explica en vez de
    bloquear), llegada estimada, buscador de aeropuertos, ruta de un itinerario en el mapa y estado vacío.
    **Error real corregido:** al editar, el formulario tomaba la hora UTC de la API como local y al guardar corría el
    viaje 5 horas (venía de la Fase 8; la evidencia 13 anterior lo hizo con su itinerario de prueba).
  - Entrega 3: pestañas con flechas, Inicio y Fin (patrón de WAI-ARIA), enlace «Saltar al contenido», avisos también al
    fallar la carga de una sección, contraste y nombres accesibles comprobados con Playwright en los dos temas.
    `test_static.py` con 7 pruebas nuevas (fuente como `font/woff2` y módulos nuevos): gateway **60 pasan**.
    `capturar_evidencias.py` confirma en el `<dialog>`, toma las capturas del CRUD sin avisos y desde el inicio de la
    página, y agrega la evidencia **21** (modo oscuro a 1280 px); evidencias 10 a 14 regeneradas con la API real.
    README, `docs/evidencias/README.md`, `docs/10` y ADR-033 actualizados. La evidencia 01 y los totales del README
    (642) conservan su fecha; el README anota los 60 del gateway.
