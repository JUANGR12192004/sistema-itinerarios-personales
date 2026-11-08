
# 06. Registro de decisiones arquitectónicas

## 1. Propósito

Registrar las decisiones arquitectónicas relevantes del Sistema de Itinerarios Personales, incluyendo su contexto, justificación, consecuencias y estado.

Las decisiones pendientes no deben considerarse definitivas hasta ser evaluadas.

## ADR-001 — Uso de microservicios

**Estado:** Aceptada para el diseño.

### Contexto

El proyecto requiere separar la consulta de aeropuertos, la gestión de itinerarios y el procesamiento de notificaciones.

### Decisión

Organizar el sistema mediante Airport Service, Itinerary Service y los componentes del sistema de notificaciones.

### Justificación

Cada componente tendrá una responsabilidad delimitada y contratos explícitos de comunicación.

### Consecuencias

- Se deben gestionar llamadas entre servicios.
- Se requiere tratamiento de errores de comunicación.
- El despliegue y las pruebas de integración serán más complejos que en una aplicación monolítica.
- Se evita concentrar toda la lógica en un único componente.

## ADR-002 — Arquitectura hexagonal

**Estado:** Aceptada para el diseño.

### Contexto

Los servicios necesitan interactuar con tecnologías externas sin acoplar sus reglas de negocio a ellas.

### Decisión

Separar dominio, casos de uso, puertos y adaptadores donde corresponda.

### Justificación

Permite sustituir dependencias externas y probar la lógica de negocio con mayor independencia de la infraestructura.

### Consecuencias

Se requiere una estructura de código más explícita, pero se facilita el mantenimiento y las pruebas.

## ADR-003 — Patrón Adapter para API Colombia

**Estado:** Aceptada para el diseño.

### Contexto

Airport Service depende de una API externa cuyo contrato puede cambiar.

### Decisión

Definir un puerto interno para consultar aeropuertos e implementar un Adapter para API Colombia.

### Justificación

La lógica interna no dependerá directamente del formato de respuesta del proveedor.

### Consecuencias

- Se necesita transformar modelos externos a modelos internos.
- Se pueden sustituir proveedores sin modificar directamente los casos de uso.
- Las pruebas del adaptador deberán verificar la traducción de datos y los errores de integración.

## ADR-004 — PostgreSQL independiente para itinerarios

**Estado:** Aceptada para el diseño.

### Contexto

Itinerary Service debe persistir y administrar itinerarios.

### Decisión

Utilizar PostgreSQL como base de datos de itinerarios y mantener la propiedad de los datos dentro de Itinerary Service.

### Justificación

El servicio controlará su esquema, sus migraciones y las operaciones sobre sus entidades.

### Consecuencias

Se deberán definir migraciones versionadas y una estrategia de respaldo y configuración.

La tecnología de persistencia del historial de notificaciones se decidirá por separado.

## ADR-005 — RabbitMQ para mensajería

**Estado:** Aceptada para el diseño.

### Contexto

El sistema debe comunicar la creación de itinerarios sin depender de que el procesamiento de notificaciones finalice en la misma solicitud HTTP.

### Decisión

Utilizar RabbitMQ para transportar eventos de integración.

### Justificación

Permite desacoplar temporalmente al productor y al consumidor.

### Consecuencias

Se deberán configurar exchanges, colas, routing keys, confirmaciones, recuperación ante errores e idempotencia.

## ADR-006 — Transactional Outbox

**Estado:** Aceptada como objetivo de implementación.

### Contexto

Guardar un itinerario y publicar un evento son operaciones que involucran dos sistemas diferentes.

### Decisión

Registrar el itinerario y el evento pendiente en una misma transacción de PostgreSQL y publicar el evento mediante un proceso independiente.

### Justificación

Reduce el riesgo de perder la publicación cuando el guardado del itinerario ya se confirmó.

### Consecuencias

Se requiere un worker o publisher, seguimiento de eventos pendientes y manejo de duplicados.

## ADR-007 — Redis para caché

**Estado:** Aceptada. Implementada en la Fase 2.

### Contexto

Las consultas repetidas pueden aumentar la latencia y la carga sobre API Colombia.

### Decisión

Incorporar Redis en Airport Service para almacenar temporalmente resultados adecuados para caché.

### Justificación

Puede reducir llamadas externas y mejorar el tiempo de respuesta.

### Consecuencias

Se deberán definir expiración, invalidación y comportamiento ante resultados obsoletos o fallos de caché.

### Definición en la Fase 2

- **Forma:** Decorator `CachedAirportProvider` que implementa el puerto `AirportProvider` y envuelve al proveedor resiliente. El Adapter no se modifica. Depende de una interfaz `CacheStore`, implementada con Redis (`RedisCacheStore`) y con un almacén en memoria en las pruebas.
- **Expiración:** cada respuesta se guarda dos veces: copia fresca de 10 minutos (`CACHE_TTL_SECONDS`) y copia de respaldo de 24 horas (`CACHE_STALE_TTL_SECONDS`).
- **Resultados obsoletos:** la copia de respaldo solo se usa como fallback cuando API Colombia no está disponible (sin conexión, 5xx, timeout o circuito abierto). La respuesta lleva `X-Cache: STALE`.
- **Qué no se guarda:** los 404 y las respuestas inválidas (502).
- **Invalidación:** solo por TTL; API Colombia cambia muy poco. Las claves llevan una versión (`airport-service:v1:...`) para descartar la caché si cambia el formato guardado.
- **Fallos de caché:** si Redis no responde, el servicio sigue funcionando sin caché, registra un warning y no vuelve a intentar con Redis durante 30 s. Un dato corrupto en la caché se ignora.
- **Cliente:** `redis` (redis-py) 8.1.0, con su versión asíncrona `redis.asyncio`.

## ADR-008 — Tecnología serverless local

**Estado:** Pendiente de decisión.

### Contexto

El proyecto debe ejecutar SendNotificationFunction en un entorno de desarrollo local.

### Alternativas

- LocalStack con AWS Lambda.
- Knative.
- OpenFaaS.

### Criterios de selección

- Facilidad de instalación.
- Compatibilidad con el equipo de desarrollo.
- Integración con el flujo de eventos.
- Complejidad de configuración.
- Facilidad para demostrar el modelo FaaS en la sustentación.

### Decisión final

Se registrará después de comparar las alternativas y comprobar su compatibilidad con el entorno.

## ADR-009 — API Gateway / BFF

**Estado:** Pendiente de selección de tecnología.

### Contexto

El frontend necesita un punto de entrada para acceder a los servicios internos.

### Decisión prevista

Utilizar un gateway que enrute solicitudes sin incorporar lógica de negocio.

### Criterios

- Facilidad de ejecución local.
- Compatibilidad con Docker.
- Enrutamiento hacia FastAPI.
- Posibilidad de incorporar rate limiting.
- Preparación para propagación de JWT.

## ADR-010 — Observabilidad

**Estado:** Aceptada para el diseño.

### Contexto

La distribución del sistema dificulta seguir una operación de extremo a extremo.

### Decisión

Incorporar OpenTelemetry, Jaeger, Prometheus y Grafana, junto con logs estructurados.

### Justificación

Estas herramientas permitirán investigar fallos y analizar trazas, métricas y comportamiento del sistema.

### Consecuencias

Se deberá configurar la instrumentación de los componentes y la propagación de identificadores de correlación.

## ADR-011 — Idioma del código y de la documentación

**Estado:** Aceptada (Fase 1).

### Contexto

El equipo escribe y sustenta en español, pero las librerías, frameworks y convenciones de programación usan el inglés. Mezclar idiomas dentro del código dificulta su lectura.

### Decisión

- El código (clases, funciones, variables, rutas, códigos de error) se escribe en inglés.
- La documentación, los comentarios y los mensajes de error para el usuario se escriben en español.
- Los términos del código siguen el lenguaje ubicuo definido en `03-dominio.md` (por ejemplo `Itinerary`, `traveler_name`, `departure_airport_id`).

### Justificación

El código queda coherente con el ecosistema (FastAPI, Pydantic, SQLAlchemy) y la documentación sigue siendo accesible para el equipo y para la evaluación del curso.

### Consecuencias

Cada término del negocio debe tener una única traducción en el código, registrada en el lenguaje ubicuo, para evitar sinónimos.

## ADR-012 — Contrato HTTP y formato único de errores

**Estado:** Aceptada (Fase 1) para Airport Service. Los endpoints de Itinerary Service se confirmarán en la Fase 3.

### Contexto

Los clientes (Itinerary Service, Gateway, Frontend) necesitan saber qué endpoints existen y cómo interpretar un error sin importar qué servicio lo generó.

### Decisión

Airport Service expone:

| Método y ruta | Éxito | Errores |
|---|---|---|
| `GET /airports` | 200 | 502, 503 |
| `GET /airports/{id}` | 200 | 404, 422, 502, 503 |
| `GET /airports/map-data` | 200 | 502, 503 |
| `GET /health` | 200 | — |

Todos los servicios responden los errores con el mismo formato:

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

Códigos HTTP: 404 recurso no encontrado, 422 validación, 502 respuesta inesperada del proveedor externo, 503 dependencia no disponible, 504 timeout (Fase 2). Los valores de `code` van en inglés y en MAYÚSCULAS_CON_GUIONES_BAJOS.

### Justificación

Un único formato permite que los clientes manejen los errores de forma uniforme, y distinguir 404, 502 y 503 permite saber si el problema es del dato solicitado, del proveedor o de la disponibilidad.

### Consecuencias

- Cada servicio necesita un manejador centralizado que traduzca las excepciones del dominio y de la aplicación a este formato.
- Cambiar un endpoint o un código de error es un cambio de contrato y debe registrarse.

## ADR-013 — Puertos para las dependencias externas de Itinerary Service

**Estado:** Aceptada (Fase 1). Corrige el diagrama de componentes de `05-diagramas.md`.

### Contexto

La primera versión del diagrama de componentes mostraba los casos de uso de Itinerary Service llamando directamente a la capa de aplicación de Airport Service y publicando directamente en RabbitMQ. Eso contradice la arquitectura hexagonal (ADR-002): un servicio no accede a las capas internas de otro, y los casos de uso no dependen de infraestructura concreta.

### Decisión

- La validación de aeropuertos se hace mediante el puerto `AirportCatalog`, implementado por `HttpAirportCatalogAdapter`, que llama al endpoint REST `GET /airports/{id}` de Airport Service.
- La publicación de eventos se hace mediante el puerto `EventPublisher`. En la Fase 4 lo implementa un publicador de RabbitMQ y en la Fase 5 un adaptador Outbox, sin cambiar el caso de uso.

### Justificación

Los casos de uso quedan independientes del protocolo HTTP y del broker de mensajería, y se pueden probar con implementaciones falsas de los puertos.

### Consecuencias

- Itinerary Service solo conoce el contrato REST publicado por Airport Service (ADR-012).
- El paso de publicación directa (Fase 4) a Outbox (Fase 5) se limita a cambiar el adaptador inyectado.

## ADR-014 — Resiliencia de Airport Service frente a API Colombia

**Estado:** Aceptada (Fase 2).

### Contexto

API Colombia es una dependencia externa que puede fallar, tardar o dejar de responder. Sin protección, cada fallo se convierte en un error para el usuario y cada demora bloquea la solicitud.

### Decisión

- **Timeout** configurable en el cliente HTTP (`API_COLOMBIA_TIMEOUT_SECONDS`, 3 s). Un timeout se reporta como `AirportProviderTimeoutError` y responde **504** `AIRPORT_PROVIDER_TIMEOUT`.
- **Retry con exponential backoff** (3 intentos; esperas de 0.5 s y 1 s, con un máximo de 4 s). Solo se reintentan los errores de disponibilidad (sin conexión, 5xx, timeout).
- **Circuit breaker** con estados CLOSED, OPEN y HALF_OPEN: se abre tras 3 consultas fallidas seguidas, rechaza las llamadas durante 30 s con **503** y luego permite una llamada de prueba.
- **Fallback:** copia de respaldo de la caché (ADR-007).
- **Orden:** caché → circuit breaker → retry con backoff → llamada con timeout → fallback. El circuit breaker envuelve al retry.
- Un 404 no se reintenta, no se guarda en caché, no abre el circuito ni activa el fallback. Un 502 tampoco se reintenta ni activa el fallback, porque el proveedor sí respondió.
- Los mecanismos se implementan en el propio código (`infrastructure/resilience`), sin librerías adicionales, y se agregan como un Decorator (`ResilientAirportProvider`) del puerto `AirportProvider`.

### Justificación

- El circuit breaker por fuera del retry evita que cada reintento cuente como un fallo distinto, y con el circuito abierto se responde al instante sin esperar timeouts ni reintentos.
- Reintentar un 404 o un 502 daría el mismo resultado: solo agregaría carga y espera.
- Implementar los mecanismos en pocas líneas propias los hace fáciles de explicar y de probar con un reloj y una espera simulados.
- Al usar Decorators, ni los casos de uso ni el Adapter cambian.

### Consecuencias

- En el peor caso (API caída y sin caché), una consulta tarda hasta 3 timeouts más las esperas del backoff antes de responder; el circuit breaker limita ese costo a las primeras consultas.
- El estado del circuit breaker vive en la memoria de cada proceso: con varias réplicas, cada una tiene el suyo.
- El backoff no usa *jitter*; si en el futuro muchos clientes reintentan a la vez, conviene agregarlo.

## ADR-015 — Reglas de negocio de Itinerary Service

**Estado:** Aceptada (Fase 3).

### Contexto

Las reglas del dominio dejaban pendientes cuatro restricciones sobre los datos de un itinerario.

### Decisión

Se confirman las siguientes reglas para la creación de un itinerario:

- El nombre del viajero no puede estar vacío ni contener solo espacios.
- El aeropuerto de salida y el de llegada deben ser diferentes.
- La duración debe ser mayor que cero minutos.
- La fecha de viaje no puede estar en el pasado al momento de crear el itinerario. La regla no aplica al actualizar.

### Justificación

Son invariantes de negocio simples que el dominio puede verificar sin depender de la infraestructura. Implementarlas en la capa de dominio evita que lleguen datos incoherentes a la base de datos.

### Consecuencias

Las excepciones del dominio (`InvalidItineraryError`) se traducen a HTTP 422 en el manejador centralizado de errores.

## ADR-016 — Un contenedor PostgreSQL por servicio

**Estado:** Aceptada (Fase 3).

### Contexto

La decisión de la base de datos dejaba abierta la opción de un servidor con bases lógicas separadas o un contenedor por servicio.

### Decisión

Un contenedor por servicio. El contenedor de Itinerary Service (`itinerary-postgres`, postgres:16-alpine) corre en el puerto 5433, con usuario y contraseña `itinerary` y base `itinerary_db`.

### Justificación

Mantener contenedores independientes refuerza la propiedad exclusiva de los datos por servicio y simplifica la configuración local. Cada servicio posee su esquema y sus migraciones sin riesgo de interferir con otros.

### Consecuencias

Hasta la Fase 10 cada servicio levanta su propio contenedor manualmente. El `docker-compose.yml` de la Fase 10 los declarará todos juntos.

## ADR-017 — travel_date con zona horaria

**Estado:** Aceptada (Fase 3).

### Contexto

El tipo de `travel_date` estaba pendiente: solo fecha, o fecha y hora con zona horaria.

### Decisión

`travel_date` es un `datetime` de Python con `tzinfo` (zona horaria explícita). La API recibe y devuelve el valor en formato ISO 8601 con offset (por ejemplo `2026-12-15T08:00:00-05:00`). El ORM almacena el valor como `TIMESTAMP WITH TIME ZONE` en PostgreSQL.

### Justificación

Es coherente con el contrato del evento `ItineraryCreatedEvent` (sección 11), que ya incluye zona horaria. Permite distinguir itinerarios en diferentes zonas y evita ambigüedades de conversión.

### Consecuencias

Las pruebas deben construir fechas con zona horaria explícita. Los esquemas Pydantic utilizan `datetime` con `AwareDatetime` para rechazar fechas sin zona en la validación de entrada.

## ADR-018 — traveler_email como campo opcional

**Estado:** Aceptada (Fase 3).

### Contexto

El campo `traveler_email` estaba pendiente de decisión.

### Decisión

`traveler_email` es un campo opcional (puede ser `None`) en la entidad `Itinerary`.

### Justificación

La notificación simulada de la Fase 6 lo necesita como destinatario, pero no todos los flujos lo requieren. Hacerlo opcional permite crear itinerarios sin correo sin romper el contrato.

### Consecuencias

El campo se incluye en el modelo ORM, las migraciones, los esquemas Pydantic y el contrato del evento. No se valida el formato del correo en el dominio; la validación de formato queda en el esquema Pydantic de entrada.

## ADR-019 — Endpoints de Itinerary Service y tratamiento de errores de Airport Service

**Estado:** Aceptada (Fase 3). Extiende ADR-012.

### Contexto

Los endpoints de Itinerary Service seguían como propuesta. Faltaba definir cómo propagar los errores de Airport Service.

### Decisión

Se confirman los endpoints de la sección 10.1. Adicionalmente, el manejador de errores de Itinerary Service distingue:

- `AirportNotFoundError` (404 de Airport Service) → HTTP 422 con código `AIRPORT_NOT_FOUND`.
- `AirportServiceUnavailableError` (503 de Airport Service o error de conexión) → HTTP 503 con código `AIRPORT_SERVICE_UNAVAILABLE`.
- `AirportServiceTimeoutError` (timeout de Airport Service, subclase de `AirportServiceUnavailableError`) → HTTP 504 con código `AIRPORT_SERVICE_TIMEOUT`.

### Justificación

Coherente con el tratamiento que Airport Service ya aplica a los timeouts de API Colombia (ADR-014): un timeout de una dependencia se propaga como 504, no como 503. Distinguir 404 de 503/504 permite que el cliente sepa si el problema es del dato solicitado o de la disponibilidad del servicio.

### Consecuencias

El adaptador `HttpAirportCatalogAdapter` debe inspeccionar el código de estado HTTP de la respuesta de Airport Service y lanzar la excepción de aplicación correspondiente.

## ADR-020 — Contrato de ItineraryCreatedEvent (versión 1)

**Estado:** Aceptada (Fase 4).

### Contexto

El contrato del evento estaba como propuesta (sección 11.1 de `CLAUDE.md`). ADR-018 indica que la notificación simulada de la Fase 6 usará `traveler_email`, pero la propuesta no lo incluía.

### Decisión

Se acepta el contrato propuesto **agregando `data.traveler_email`** (texto o `null`):

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

- `occurred_at` va en UTC con sufijo `Z`; `travel_date` conserva la zona horaria del viajero (ADR-017).
- `correlation_id` es el header `X-Correlation-ID` de la solicitud HTTP; si no llega, se genera un UUID.
- El evento se modela como `ItineraryCreatedEvent` en la capa de **aplicación** (no en el dominio), porque es un contrato público entre contextos.

### Justificación

Incluir `traveler_email` desde la versión 1 evita publicar una versión 2 en la Fase 6 solo para agregar el destinatario. Al ser opcional, los itinerarios sin correo siguen siendo válidos.

### Consecuencias

El contrato se documenta en `docs/asyncapi/asyncapi.yaml`. Las pruebas de `tests/application/test_events.py` fallan si la forma del evento cambia. Un cambio incompatible exige una nueva `event_version`.

## ADR-021 — Topología de RabbitMQ y librería pika

**Estado:** Aceptada (Fase 4).

### Contexto

La topología estaba como propuesta (sección 11.2 de `CLAUDE.md`) y faltaba elegir la librería cliente. Itinerary Service es completamente síncrono (rutas `def`, SQLAlchemy y httpx síncronos).

### Decisión

- Exchange `itinerary.events` (tipo `topic`, durable), routing key `itinerary.created`.
- Cola `notification.itinerary-created` (durable), con dead letter exchange `itinerary.events.dlx` (tipo `direct`, durable) y cola de mensajes fallidos `notification.itinerary-created.dlq` (durable).
- Mensajes persistentes (`delivery_mode=2`), `content_type=application/json`, `message_id = event_id`, `type = event_type` y `correlation_id` en las propiedades AMQP.
- Publisher confirms y `mandatory=True`: la publicación solo se considera exitosa si RabbitMQ confirma que el mensaje llegó a una cola.
- Librería **pika 1.3.2** (cliente síncrono oficial de RabbitMQ). Se abre una conexión por publicación, porque `BlockingConnection` no es segura entre hilos y FastAPI ejecuta las rutas `def` en varios hilos.
- Mientras no exista el consumidor (Fase 6), el publicador declara toda la topología (las declaraciones son idempotentes), para que ningún mensaje se pierda por falta de cola.

### Justificación

pika encaja con el código síncrono sin puentes entre hilos y *event loop* (se descartó aio-pika por esa razón). Una conexión por publicación es simple de explicar y suficiente para el volumen del proyecto.

### Consecuencias

El consumidor de la Fase 6 debe declarar la cola con los mismos argumentos (si no, RabbitMQ responde `PRECONDITION_FAILED`). Abrir una conexión por publicación añade algunos milisegundos por solicitud; si fuera un problema, se reemplazaría por una conexión compartida protegida.

## ADR-022 — Publicación directa tras el commit (Fase 4)

**Estado:** Aceptada (Fase 4). Se reemplaza por el Transactional Outbox en la Fase 5 (ADR-006).

### Contexto

En la Fase 3 el commit ocurría en la dependencia `get_db_session`, **después** de que el caso de uso llamaba al publicador. La Fase 4 pide publicar directamente **tras el commit**, para mostrar después el problema de *double write*.

### Decisión

- Nuevo puerto `UnitOfWork` (`commit()`), implementado por `SqlAlchemyUnitOfWork` sobre la misma sesión del repositorio.
- El puerto `EventPublisher` pasa a `publish(event: ItineraryCreatedEvent)` y sus adaptadores envuelven los errores técnicos en `EventPublishError`.
- `CreateItineraryUseCase` sigue el orden: guardar → `commit()` → construir el evento → `publish()`.
- Si la publicación falla después del commit, `POST /itineraries` responde **201** y se registra un `ERROR` "Evento perdido" con el id del itinerario y el `event_id`.

### Justificación

Publicar antes del commit podría anunciar un itinerario que luego no se guarda. Responder 503 cuando el itinerario sí quedó guardado engañaría al cliente y lo llevaría a reintentar y duplicarlo. El 201 con log de error describe lo que realmente pasó.

### Consecuencias

Si RabbitMQ falla tras el commit, el evento se pierde: es el problema de *double write* (dos escrituras en sistemas distintos sin una transacción común). La Fase 5 lo resuelve guardando el evento en `outbox_events` en la misma transacción, cambiando solo el adaptador inyectado de `EventPublisher`.

## ADR-023 — SonarCloud para el análisis de calidad del código

**Estado:** Aceptada (agregada en el PR #7, rama `chore/sonarcloud-config`).

### Contexto

Las pruebas (pytest y la integración continua de `.github/workflows/tests.yml`) comprueban que el código **funciona**, pero no revisan su **calidad**: código duplicado, funciones demasiado complejas, malas prácticas o posibles problemas de seguridad. El equipo quería esa revisión automática en cada pull request.

### Decisión

- Usar **SonarCloud** (servicio en la nube de SonarSource para análisis estático) con **Automatic Analysis**: el equipo conectó el repositorio desde SonarCloud con su GitHub App, y SonarCloud analiza por su cuenta cada push a `main` y cada pull request. **No hay ningún paso en GitHub Actions** ni token en el repositorio.
- Con Automatic Analysis la configuración no va en `sonar-project.properties` sino en `.sonarcloud.properties`, en la raíz del repositorio:

| Propiedad | Valor | Efecto |
|---|---|---|
| `sonar.python.version` | `3.12` | Aplica las reglas de Python 3.12 (sin ella, SonarCloud asume compatibilidad con varias versiones de 3.x) |
| `sonar.sources` | `services` | Código de producción: todo lo que está dentro de `services/` |
| `sonar.exclusions` | `**/tests/**,**/alembic/versions/**` | Las pruebas y las migraciones generadas por Alembic no cuentan como código de producción |
| `sonar.tests` | `services` | Las pruebas se buscan dentro de `services/` |
| `sonar.test.inclusions` | `**/tests/**` | Solo las carpetas `tests/` se tratan como código de pruebas |

### Qué analiza

El código Python de producción de Airport Service e Itinerary Service: *bugs*, vulnerabilidades, *security hotspots* (puntos que una persona debe revisar, por ejemplo credenciales en el código o escuchar en `0.0.0.0`), *code smells* (problemas de mantenibilidad, como complejidad alta) y código duplicado. Las pruebas se reconocen como pruebas y se revisan con las reglas propias de código de pruebas.

### Justificación

Automatic Analysis no necesita configurar un *workflow* ni guardar un token como secreto, y es gratuito para repositorios públicos. Separar fuentes y pruebas evita falsos positivos (por ejemplo, credenciales de ejemplo en las pruebas marcadas como vulnerabilidad del servicio) y que las migraciones generadas automáticamente cuenten como duplicación.

### Consecuencias

- Automatic Analysis **no importa reportes de cobertura**: SonarCloud no muestra el porcentaje de cobertura de pytest. Si se quisiera, habría que cambiar a análisis desde GitHub Actions (con token).
- Solo se analiza `services/`. Cuando existan `serverless/`, `gateway/` y `frontend/` (Fases 6 a 8), hay que agregarlos a `sonar.sources` si se quiere analizarlos.
- El acuerdo del equipo para fusionar exige el check "Pruebas" y una aprobación; el resultado de SonarCloud (su *Quality Gate*) no forma parte de ese acuerdo por ahora.

## 2. Revisión de decisiones

Las decisiones pendientes deberán resolverse antes de implementar los componentes afectados.

Toda modificación de una decisión aceptada deberá incluir la razón del cambio y sus consecuencias.
