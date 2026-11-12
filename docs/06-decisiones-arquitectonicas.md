
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

La tecnología de persistencia del historial de notificaciones se decidió por separado en la Fase 6 (ADR-029).

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

**Estado:** Aceptada. Se implementa en la Fase 5; los detalles están en ADR-024 (tabla `outbox_events`), ADR-025 (Outbox Relay) y ADR-026 (registro del evento en la misma transacción).

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

**Estado:** Aceptada (Fase 6, entrega 6A).

### Contexto

El proyecto debe ejecutar SendNotificationFunction en un entorno de desarrollo local. El profesor no exige una plataforma serverless específica. El equipo trabaja en Windows 11 y la solución también debe funcionar en macOS con Apple Silicon.

### Criterios de selección

- Facilidad de instalación.
- Compatibilidad con el equipo de desarrollo.
- Integración con el flujo de eventos.
- Complejidad de configuración.
- Facilidad para demostrar el modelo FaaS en la sustentación.

### Alternativas evaluadas

| Alternativa | Qué necesita | Resultado |
|---|---|---|
| **Imagen oficial de AWS Lambda para Python 3.12 con el Runtime Interface Emulator (RIE)** | Solo Docker | **Elegida** |
| LocalStack con AWS Lambda | Docker, más una cuenta de LocalStack y un *auth token* (obligatorios desde marzo de 2026) | Descartada: cada integrante dependería de una cuenta externa |
| Knative | Un clúster de Kubernetes (kind, minikube o el de Docker Desktop) con Knative Serving y Eventing | Descartada: su instalación es mucho más compleja que el resto del proyecto |
| OpenFaaS | Kubernetes (o faasd, que necesita Linux con containerd) | Descartada: por la misma razón que Knative |

### Decisión

- SendNotificationFunction se empaqueta como una **imagen de contenedor de Lambda** construida desde `public.ecr.aws/lambda/python:3.12`.
- La imagen trae el cliente del runtime de Lambda (`awslambdaric`) y el **Runtime Interface Emulator**. En local, el RIE hace el papel del servicio AWS Lambda: recibe la invocación, llama al handler y devuelve su resultado.
- El RIE escucha en el puerto 8080 del contenedor, que se publica como **9000** en el equipo (sección 7.6 de `CLAUDE.md`):

```
POST http://localhost:9000/2015-03-31/functions/function/invocations
```

- Es la misma ruta de la API *Invoke* de AWS Lambda. El cuerpo de la solicitud es el `event` que recibe el handler, y la respuesta es lo que el handler devuelve.

### Justificación

- Solo necesita Docker Desktop, que el equipo ya usa desde la Fase 2.
- Funciona igual en Windows 11 y en macOS con Apple Silicon: la imagen es multiarquitectura (amd64 y arm64).
- La misma imagen se puede desplegar en AWS Lambda sin cambios (subiéndola a Amazon ECR).
- Permite demostrar el modelo FaaS sin cuentas externas ni Kubernetes.

### Limitaciones en local (y por qué la función sigue siendo FaaS)

- **No hay escalado automático:** un contenedor es una sola instancia de la función y atiende una invocación a la vez.
- **No se apaga cuando no hay eventos** (no hay *scale to zero*): el contenedor queda encendido. Sí se puede ver el arranque en frío: la primera invocación inicializa la función y tarda más.
- **No hay facturación por invocación, límites de concurrencia ni Event Source Mapping.** Por eso existe el Event Trigger (entrega 6B), que cumple el papel del Event Source Mapping.

Lo que hace FaaS a una función es su **modelo de programación y su contrato con la plataforma**: es una función `handler(event, context)` que invoca la plataforma, sin servidor propio y sin estado entre invocaciones (ADR-028). Eso se cumple igual en local y en AWS. Las limitaciones anteriores son de la **operación** de la plataforma local, no del código: la misma imagen, desplegada en AWS Lambda, escalaría y se apagaría sola.

## ADR-009 — API Gateway con Nginx

**Estado:** Aceptada (Fase 7, entrega 7A). Antes se llamaba "API Gateway / BFF" y estaba pendiente de seleccionar la tecnología.

### Contexto

El frontend (Fase 8) y cualquier otro cliente necesitan un **punto único de entrada** a los servicios internos. Ese punto debe enrutar, aplicar rate limiting y preparar la propagación de JWT, **sin lógica de negocio**: las reglas viven en el dominio de cada servicio (ADR-002, ADR-015). Si se copiaran en el gateway, habría dos fuentes de verdad y cada cambio de negocio obligaría a desplegar un componente que comparten todos.

Un **API Gateway** es genérico: no conoce el dominio y se ocupa de tareas transversales (enrutamiento, límites, correlación, autenticación). Un **BFF** (*Backend for Frontend*) es un backend hecho a la medida de un frontend concreto, que sí junta y transforma respuestas para la pantalla. El proyecto necesita lo primero.

La comunicación interna Itinerary Service → Airport Service (validar aeropuertos) **no pasa por el gateway**: el gateway solo atiende las solicitudes que entran desde afuera.

### Alternativas evaluadas

| Criterio | Nginx | Traefik | Kong (sin base de datos) | BFF en FastAPI |
|---|---|---|---|---|
| Facilidad de uso | Alta: un archivo declarativo | Media | Baja: services, routes, plugins | Alta para el equipo, pero el proxy se programa a mano |
| Rate limiting nativo | Sí (`limit_req`) | Sí (middleware) | Sí (plugin) | No (a mano o `slowapi`) |
| 429 con el formato de la sección 10.2 | Sí (`error_page` + `return`) | Texto fijo; el JSON exige un servicio extra | JSON propio de Kong | Sí |
| Evita lógica de negocio por accidente | Muy bien: sin scripting (no se carga `njs`) | Bien | Regular: plugins Lua ejecutan código | Mal: es código Python |
| Apple Silicon y Windows | Imagen oficial arm64 y amd64 | Sí | Sí | Sí |
| Docker Compose (Fase 10) | Simple (plantillas con variables) | Excelente (labels) | Correcta, pero pesada | Necesita su `Dockerfile` |
| Validar la configuración en CI | `nginx -t` | Limitada | `kong config parse` | pytest |
| Servir el frontend en el mismo origen (Fase 8) | Sí | No | No | Sí |
| JWT a futuro | Solo lo reenvía (la versión libre no lo valida) | `ForwardAuth` | Plugin JWT nativo | Con una librería |

### Decisión

- **Nginx** como gateway puro, en Docker con la imagen oficial **`nginx:1.30.6-alpine`** (versión estable, arm64 y amd64). La carpeta `gateway/` tiene un `Dockerfile` que solo parte de esa imagen y copia la plantilla `templates/default.conf.template`. Se usa un `Dockerfile` y no un volumen porque la ruta del volumen se escribe distinto en PowerShell, CMD y zsh.
- **Enrutamiento:** `/api/airports` y `/api/airports/...` → Airport Service (`/airports...`); `/api/itineraries` y `/api/itineraries/...` → Itinerary Service (`/itineraries...`). El gateway quita el prefijo `/api` y traduce de vuelta las redirecciones de los servicios (`proxy_redirect`). Cualquier otra ruta → 404 `ROUTE_NOT_FOUND`.
- **Direcciones de los servicios por variables de entorno** (`AIRPORT_SERVICE_UPSTREAM`, `ITINERARY_SERVICE_UPSTREAM`), que la imagen oficial reemplaza en la plantilla al arrancar (`envsubst`, limitado por `NGINX_ENVSUBST_FILTER`). En la Fase 7 los servicios corren con uvicorn en el equipo y el gateway llega a ellos por `host.docker.internal:8001/8002`. En la Fase 10 solo cambian por los nombres de los contenedores. En Linux (el CI) hace falta `--add-host=host.docker.internal:host-gateway`.
- **Headers reenviados:** `Authorization` tal cual, sin validarlo (preparación de JWT; nunca se escribe en el log), `X-Correlation-ID`, `Host`, `X-Real-IP`, `X-Forwarded-For` y `X-Forwarded-Proto`.
- **X-Correlation-ID:** si llega con un formato seguro (`^[A-Za-z0-9._-]{1,128}$`) se reenvía. Si falta o no es válido, el gateway genera uno con forma de UUID a partir de `$request_id`. Se valida porque el valor se escribe dentro del JSON de los errores y en el log. La respuesta lleva un solo header `X-Correlation-ID` (el del servicio se oculta; es el mismo valor) y el log de acceso incluye `correlation_id` (preparación de la Fase 9).
- **Timeouts:** conexión 2 s (`GATEWAY_PROXY_CONNECT_TIMEOUT`) y lectura/escritura 15 s (`GATEWAY_PROXY_READ_TIMEOUT`). La lectura es mayor que los timeouts internos (Itinerary → Airport: 2 × 5 s; Airport → API Colombia: 3 intentos de 3 s más las esperas, ADR-014), para que el servicio alcance a responder su propio error. `proxy_next_upstream off`: el gateway no reintenta (los reintentos están en los servicios y reintentar un `POST` podría duplicar un itinerario). `max_fails=0`: Nginx nunca marca un servicio como caído por su cuenta.
- **Errores propios del gateway** con el formato de la sección 10.2, nunca con la página HTML de Nginx: 502 `UPSTREAM_UNAVAILABLE` (el servicio no acepta la conexión), 504 `UPSTREAM_TIMEOUT`, 404 `ROUTE_NOT_FOUND`, 413 `PAYLOAD_TOO_LARGE` (cuerpo de más de 1 MB). Los 502 y 504 indican el servicio en `details.service`. Con `proxy_intercept_errors off`, las respuestas de error **de los servicios** (sus 404, 422, 502, 503, 504) pasan sin cambios. Se eligió 502 (y no 503) porque es el código HTTP estándar cuando un gateway no logra hablar con el servidor de atrás. Así el cliente distingue entre "el gateway no llega al servicio" (502) y "el servicio responde, pero su dependencia no está disponible" (503).
- **Rate limiting (entrega 7B):** por IP de origen (`$binary_remote_addr`), 10 solicitudes por segundo con ráfaga de 20 (`nodelay`), solo en `/api/`. Al superarlo: 429 `RATE_LIMIT_EXCEEDED` con el formato de la sección 10.2 y header `Retry-After`.
- **Otras rutas:** `GET /health` del propio gateway (`{"status": "ok", "service": "api-gateway"}`, no consulta a los servicios) y `/` reservada para el frontend de la Fase 8 (por ahora, un texto). Swagger (`/docs`) de cada servicio no se expone por el gateway.
- **Sin CORS:** el frontend se servirá desde el mismo origen (Fase 8).
- `server_tokens off` (no revela la versión de Nginx).

### Justificación

Nginx cumple todos los requisitos de la fase con configuración declarativa. Su `limit_req` es nativo y permite responder los errores en el formato propio del proyecto. Además, su configuración no deja lugar a lógica de negocio, se valida con `nginx -t` y en la Fase 8 sirve el frontend desde el mismo origen. Traefik destaca en el descubrimiento de contenedores, pero no responde el 429 en JSON sin un servicio adicional ni sirve archivos estáticos. Kong es más pesado y permite ejecutar código en plugins. Un BFF en FastAPI invitaría a agregar lógica y es otro patrón.

### Consecuencias

- La versión libre de Nginx **no valida JWT**. Si más adelante hiciera falta validarlo en el gateway, habría que usar `auth_request` hacia un servicio de autenticación o reconsiderar Kong.
- Nginx resuelve los nombres de los servicios **al arrancar**. Si un nombre no existe, el gateway no inicia. Con `host.docker.internal` no pasa en Docker Desktop. En la Fase 10 habrá que tenerlo en cuenta (orden de arranque o resolución dinámica).
- En Docker Desktop, todas las solicitudes hechas desde el propio equipo llegan al contenedor con la misma IP (`192.168.65.1`), así que localmente el límite de solicitudes es compartido.
- En zsh, las URL con `?` deben ir entre comillas en `curl` (si no, zsh intenta expandirlas como un patrón de archivos).

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
- La publicación de eventos se hace mediante el puerto `EventPublisher`. En la Fase 4 lo implementa un publicador de RabbitMQ y en la Fase 5 un adaptador Outbox. El caso de uso sigue dependiendo solo del puerto, pero en la Fase 5 cambia el **orden** de sus pasos: registra el evento antes del commit (ADR-026).

### Justificación

Los casos de uso quedan independientes del protocolo HTTP y del broker de mensajería, y se pueden probar con implementaciones falsas de los puertos.

### Consecuencias

- Itinerary Service solo conoce el contrato REST publicado por Airport Service (ADR-012).
- El paso de publicación directa (Fase 4) a Outbox (Fase 5) cambia el adaptador inyectado y el orden del caso de uso (registrar el evento → commit), sin que el caso de uso conozca RabbitMQ ni la tabla de la outbox.
- *Corrección (Fase 5):* la versión anterior de esta decisión decía que bastaba con cambiar el adaptador "sin cambiar el caso de uso". No es así: si el caso de uso hiciera el commit antes de llamar al puerto, la fila de la outbox quedaría fuera de la transacción del itinerario y volvería el problema de *double write*. Ver ADR-026.

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
- Mientras no exista el consumidor (Fase 6), el publicador declara toda la topología (las declaraciones son idempotentes), para que ningún mensaje se pierda por falta de cola. *Corrección (Fase 6, ADR-032):* desde la entrega 6B el publicador declara **solo el exchange** `itinerary.events`; la cola, su binding, la DLX y la DLQ las declara el Event Trigger, que es su dueño.

### Justificación

pika encaja con el código síncrono sin puentes entre hilos y *event loop* (se descartó aio-pika por esa razón). Una conexión por publicación es simple de explicar y suficiente para el volumen del proyecto.

### Consecuencias

El consumidor de la Fase 6 debe declarar la cola con los mismos argumentos (si no, RabbitMQ responde `PRECONDITION_FAILED`). Abrir una conexión por publicación añade algunos milisegundos por solicitud; si fuera un problema, se reemplazaría por una conexión compartida protegida.

## ADR-022 — Publicación directa tras el commit (Fase 4)

**Estado:** Reemplazada en la Fase 5 por el Transactional Outbox (ADR-006 y ADR-024 a ADR-026). Se conserva como registro histórico.

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

Si RabbitMQ falla tras el commit, el evento se pierde: es el problema de *double write* (dos escrituras en sistemas distintos sin una transacción común). La Fase 5 lo resuelve guardando el evento en `outbox_events` en la misma transacción: cambia el adaptador inyectado de `EventPublisher` **y** el orden del caso de uso, que registra el evento antes del commit (ADR-026).

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
| `sonar.sources` | `services,serverless` | Código de producción: todo lo que está dentro de `services/` y, desde la Fase 6, de `serverless/` |
| `sonar.exclusions` | `**/tests/**,**/alembic/versions/**` | Las pruebas y las migraciones generadas por Alembic no cuentan como código de producción |
| `sonar.tests` | `services,serverless` | Las pruebas se buscan dentro de `services/` y `serverless/` |
| `sonar.test.inclusions` | `**/tests/**` | Solo las carpetas `tests/` se tratan como código de pruebas |

### Qué analiza

El código Python de producción de Airport Service e Itinerary Service: *bugs*, vulnerabilidades, *security hotspots* (puntos que una persona debe revisar, por ejemplo credenciales en el código o escuchar en `0.0.0.0`), *code smells* (problemas de mantenibilidad, como complejidad alta) y código duplicado. Las pruebas se reconocen como pruebas y se revisan con las reglas propias de código de pruebas.

### Justificación

Automatic Analysis no necesita configurar un *workflow* ni guardar un token como secreto, y es gratuito para repositorios públicos. Separar fuentes y pruebas evita falsos positivos (por ejemplo, credenciales de ejemplo en las pruebas marcadas como vulnerabilidad del servicio) y que las migraciones generadas automáticamente cuenten como duplicación.

### Consecuencias

- Automatic Analysis **no importa reportes de cobertura**: SonarCloud no muestra el porcentaje de cobertura de pytest. Si se quisiera, habría que cambiar a análisis desde GitHub Actions (con token).
- Se analizan `services/` y, desde la entrega 6C, `serverless/` (SendNotificationFunction y el Event Trigger). Cuando existan `gateway/` y `frontend/` (Fases 7 y 8), hay que agregarlos a `sonar.sources` si se quiere analizarlos.
- El acuerdo del equipo para fusionar exige el check "Pruebas" y una aprobación; el resultado de SonarCloud (su *Quality Gate*) no forma parte de ese acuerdo por ahora.

## ADR-024 — Tabla `outbox_events` y `OutboxMessage` (Fase 5)

**Estado:** Aceptada (Fase 5, entrega 5A).

### Contexto

El Transactional Outbox (ADR-006) necesita guardar cada evento pendiente en la **misma base de datos** que el itinerario, para que ambos entren en una sola transacción de PostgreSQL. Hace falta definir la tabla, cómo se buscan rápido los pendientes y qué pasa con los ya publicados.

### Decisión

- Nueva tabla `outbox_events`, creada con una migración de Alembic:

| Columna | Tipo | Significado |
|---|---|---|
| `id` | UUID, clave primaria | Igual al `event_id` del evento: una fila por evento |
| `aggregate_type` | VARCHAR(100) | Tipo del agregado que originó el evento (`itinerary`) |
| `aggregate_id` | UUID | Id del agregado (el `itinerary_id`) |
| `event_type` | VARCHAR(100) | `itinerary.created` |
| `event_version` | INTEGER | Versión del contrato (`1`) |
| `payload` | JSONB | El evento completo, con la forma exacta del contrato (ADR-020) |
| `occurred_at` | TIMESTAMPTZ | Cuándo ocurrió el hecho |
| `published_at` | TIMESTAMPTZ, nulo | `NULL` mientras está pendiente; la fecha de publicación después |
| `attempts` | INTEGER, por defecto 0 | Intentos de publicación fallidos |
| `last_error` | TEXT, nulo | Último error de publicación |
| `failed_at` | TIMESTAMPTZ, nulo | Agregada por ADR-027 (migración `c4d8e2f6a9b1`): fecha del fallo permanente de un mensaje venenoso; `NULL` si no lo hubo |

- **Índice parcial** `ix_outbox_events_pending` sobre `occurred_at` con la condición `WHERE published_at IS NULL` (desde ADR-027: `WHERE published_at IS NULL AND failed_at IS NULL`). Un índice parcial solo incluye las filas que cumplen la condición: contiene únicamente los pendientes, así que sigue siendo pequeño aunque la tabla crezca, y sirve para la consulta del relay (`WHERE published_at IS NULL ORDER BY occurred_at`).
- En el código, cada fila es un **`OutboxMessage`** ("mensaje pendiente" en el lenguaje ubicuo), un `dataclass` de la capa de **aplicación**. No va en el dominio porque es un concepto técnico de entrega de mensajes, no una regla del negocio de itinerarios. El modelo ORM `OutboxEventORM` vive en `infrastructure/persistence`.
- Los eventos publicados **se conservan** en la tabla. La limpieza periódica queda como mejora futura.

### Justificación

`payload` en JSONB guarda el contrato tal cual se publicará: el relay no necesita leer la tabla `itineraries` ni reconstruir datos. `id = event_id` impide registrar dos veces el mismo evento (la clave primaria lo rechazaría). Las columnas `aggregate_*`, `event_type` y `event_version` permiten consultar y depurar la outbox sin abrir el JSON. Conservar los publicados ayuda a demostrar y auditar el flujo.

### Consecuencias

- La tabla crece con cada itinerario creado; con el índice parcial la búsqueda de pendientes no se vuelve lenta, pero en un sistema real habría que borrar o archivar los publicados antiguos.
- `outbox_events` pertenece a Itinerary Service, como `itineraries` (ADR-004): ningún otro servicio la lee.

## ADR-025 — Outbox Relay: proceso aparte, `SKIP LOCKED` y entrega al menos una vez (Fase 5)

**Estado:** Aceptada (Fase 5). Se implementa en la entrega 5B.

### Contexto

Alguien debe leer los eventos pendientes de `outbox_events` y publicarlos en RabbitMQ, sin bloquear la API y sin que dos copias del proceso publiquen el mismo evento a la vez.

### Decisión

- El **Outbox Relay** es un proceso aparte de Itinerary Service, con su propio comando (`python -m app.outbox_relay`). Cada ciclo procesa un lote y espera un intervalo. Variables: `OUTBOX_RELAY_POLL_INTERVAL_SECONDS` (por defecto 2) y `OUTBOX_RELAY_BATCH_SIZE` (por defecto 10). Se detiene con Ctrl+C. Si PostgreSQL falla en un ciclo, registra el error y sigue con el siguiente, sin terminar el proceso.
- Toma los pendientes con `SELECT ... WHERE published_at IS NULL ORDER BY occurred_at LIMIT n FOR UPDATE SKIP LOCKED`. `FOR UPDATE` bloquea las filas leídas hasta el fin de la transacción, y `SKIP LOCKED` hace que otro relay **salte** las filas bloqueadas en vez de esperarlas: dos relays nunca toman el mismo evento.
- **Un commit por lote**: hacer commit evento por evento liberaría los bloqueos del resto del lote, que otro relay podría tomar mientras este todavía los publica.
- Orden: **publicar y después marcar** `published_at`. Esto da una entrega **al menos una vez**.
- Si una publicación falla: se incrementa `attempts`, se guarda `last_error`, el evento sigue pendiente y **se detiene el lote**. Los eventos restantes no se tocan ni suman intentos, y todos se reintentan en el siguiente ciclo. Si RabbitMQ está caído, seguir con el resto solo alargaría el ciclo (cada intento espera hasta `RABBITMQ_TIMEOUT_SECONDS`).
- Si el `payload` no se puede leer o el `event_type` es desconocido, el relay **continúa** con el siguiente, porque ese fallo no depende de RabbitMQ. *Corrección (ADR-027):* la primera versión solo sumaba el intento y el mensaje seguía pendiente; ahora es un fallo permanente y se marca con `failed_at`.
- No hay límite de intentos para los fallos temporales (ADR-027).

### Justificación

Un proceso aparte desacopla la respuesta HTTP de la disponibilidad de RabbitMQ: la API responde 201 aunque el broker esté caído. `SKIP LOCKED` permite correr varios relays sin coordinación extra. Publicar antes de marcar evita el caso grave (marcar como publicado algo que nunca salió); el precio son los duplicados ocasionales, que el consumidor absorbe.

### Consecuencias

- **Puede haber duplicados.** Si el relay publica y se detiene (o PostgreSQL falla) antes del commit que marca `published_at`, la transacción se deshace, el evento sigue pendiente y se publicará otra vez. Como el commit es por lote, puede repetirse hasta un lote completo. Por eso el consumidor de la Fase 6 **debe ser idempotente** con `event_id`, que ya viaja como `message_id` (ADR-021).
- Los mensajes ilegibles ya no bloquean el relay: ADR-027 los descarta con `failed_at`. Un evento que RabbitMQ rechace siempre (`EventPublishError` permanente) sí seguiría deteniendo cada lote; ver las consecuencias de ADR-027.
- El evento llega a RabbitMQ con un pequeño retraso (como máximo, el intervalo de revisión más el tiempo de publicación).
- `RabbitMQEventPublisher` abre una conexión por publicación (ADR-021); con lotes pequeños es aceptable.

## ADR-026 — Registro del evento en la misma transacción del itinerario (Fase 5)

**Estado:** Aceptada (Fase 5, entrega 5A). Reemplaza a ADR-022.

### Contexto

En la Fase 4 `CreateItineraryUseCase` hacía guardar → commit → publicar (ADR-022). Si RabbitMQ fallaba después del commit, el evento se perdía (*double write*). Para que el Outbox funcione, el evento debe quedar registrado **dentro** de la transacción del itinerario.

### Decisión

- El puerto `EventPublisher.publish(event)` se mantiene, con dos adaptadores:

| Quién lo usa | Adaptador | Qué hace |
|---|---|---|
| `CreateItineraryUseCase` (API) | `OutboxEventPublisher` | Agrega la fila a `outbox_events` en la **misma sesión** de SQLAlchemy del repositorio, sin hacer commit |
| `OutboxRelay` (proceso aparte, 5B) | `RabbitMQEventPublisher` (sin cambios) | Publica en RabbitMQ |

- Nuevo orden del caso de uso: validar aeropuertos → crear `Itinerary` → `save()` → construir el evento → `publish()` (registro en la outbox) → `commit()`.
- Se elimina el `try/except EventPublishError` con el log "Evento perdido": si el evento no se puede registrar, el error se propaga, la transacción se deshace y no se guarda nada (500 `INTERNAL_ERROR`). Si el commit falla, tampoco se guarda ninguno de los dos.
- `ItineraryCreatedEvent.from_dict(payload)` reconstruye el evento desde el JSON guardado, para que el relay reutilice `RabbitMQEventPublisher` con las mismas propiedades AMQP.
- El contrato del evento (ADR-020) y la topología (ADR-021) **no cambian**.

### Justificación

El caso de uso sigue sin conocer RabbitMQ ni la outbox (depende solo de puertos, ADR-002), pero decide el orden: el evento debe registrarse antes del commit para quedar en la misma transacción. Así el itinerario y su evento se guardan juntos o no se guarda ninguno. Reutilizar `RabbitMQEventPublisher` evita duplicar la lógica de publicación.

### Consecuencias

- `POST /itineraries` ya no habla con RabbitMQ: responde 201 aunque RabbitMQ esté caído, y el evento queda pendiente hasta que el relay lo publique.
- Mientras no exista el relay (entre las entregas 5A y 5B), los eventos se acumulan como pendientes en la tabla.
- La API depende solo de PostgreSQL para crear itinerarios (además de Airport Service).

## ADR-027 — Mensajes venenosos en la outbox: fallo temporal vs. fallo permanente (Fase 5)

**Estado:** Aceptada (Fase 5, primer commit de la entrega 5C). Amplía ADR-024 y ADR-025.

### Contexto

Un **mensaje venenoso** (*poison message*) es un mensaje que siempre falla al procesarse, por mucho que se reintente. En la outbox ocurre cuando el `payload` no se puede leer (le falta un campo, un UUID es inválido, la versión no existe) o cuando el `event_type` es desconocido.

En la entrega 5B el relay le sumaba un intento (`mark_failed`), pero el mensaje seguía pendiente (`published_at` nulo). Esto causaba tres problemas:

1. Se volvía a leer y a fallar en **cada ciclo, para siempre**.
2. Llenaba el log con el mismo error cada pocos segundos.
3. Como se leen los más antiguos primero, si se acumulaban tantos mensajes ilegibles como `OUTBOX_RELAY_BATCH_SIZE`, ocupaban todo el lote y el relay **nunca volvía a publicar un evento válido**.

### Decisión

- El relay distingue dos tipos de fallo:

| Tipo | Causa | Qué hace el relay |
|---|---|---|
| **Temporal** | `EventPublishError` (por ejemplo, RabbitMQ caído) | `mark_failed`: suma `attempts`, guarda `last_error`, el evento **sigue pendiente** y se detiene el lote. Se reintenta en el siguiente ciclo, **sin máximo de intentos** |
| **Permanente** | `payload` ilegible o `event_type` desconocido | `mark_dead`: suma `attempts`, guarda `last_error` y la fecha en **`failed_at`**. El mensaje **deja de estar pendiente**, no se reintenta y el lote **continúa** |

- Nueva columna `failed_at` (TIMESTAMPTZ, nula) en `outbox_events`, con la migración `c4d8e2f6a9b1`.
- Nuevo método del puerto `OutboxRepository.mark_dead(message_id, failed_at, error)`.
- Pendiente = `published_at IS NULL AND failed_at IS NULL`. `get_pending` usa esa condición, y el índice parcial `ix_outbox_events_pending` se recrea con la misma condición. Un índice parcial no se puede modificar, así que la migración lo borra y lo crea de nuevo.
- `RelayResult` separa `failed` (temporales) de `dead` (descartados). El log del relay registra cada mensaje descartado en `ERROR`, una sola vez.
- Los descartados **cuentan** para el "lote completo" del bucle (el siguiente ciclo empieza sin esperar); los fallos temporales no, para no reintentar sin pausa cuando RabbitMQ está caído.

### Justificación

Un fallo temporal se arregla solo cuando vuelve la dependencia; descartar el evento sería perderlo, que es justo lo que el Outbox evita. Por eso no hay máximo de intentos: un RabbitMQ caído durante horas no debe descartar eventos válidos. Un fallo permanente, en cambio, no se arregla reintentando: sacarlo de los pendientes protege a los eventos válidos que vienen detrás. La fila **no se borra**: queda en la tabla con su error para que una persona la revise.

### Relación con la DLQ de RabbitMQ

Es la misma idea que la **dead letter queue** (DLQ) de la topología (ADR-021), aplicada en el otro extremo del flujo:

| | `failed_at` en `outbox_events` | DLQ `notification.itinerary-created.dlq` |
|---|---|---|
| Dónde actúa | En el **productor**, antes de publicar | En el **consumidor** (Fase 6), después de publicar |
| Qué aparta | Mensajes que el relay no puede convertir en evento | Mensajes que el consumidor rechaza sin reencolar |
| Para qué | Que no bloqueen la publicación de los demás | Que no bloqueen el consumo de los demás |
| Qué se hace después | Revisar la fila (`last_error`) y corregirla a mano | Revisar el mensaje en la DLQ |

Un mensaje descartado con `failed_at` **nunca llega a RabbitMQ**, así que tampoco llega a la DLQ.

### Consecuencias

- Un mensaje descartado no se publica nunca solo. Para reintentarlo después de corregirlo, hay que dejar `failed_at` en `NULL` a mano (`UPDATE outbox_events SET failed_at = NULL WHERE id = ...`).
- Todo `EventPublishError` se trata como temporal, incluidos rechazos de RabbitMQ que podrían ser permanentes (`NackError`). Si ocurrieran, ese evento detendría cada lote. Distinguirlos queda como mejora futura. *Actualización (Fase 6, ADR-032):* `UnroutableError` (ninguna cola recibió el mensaje) **sí es temporal**: ocurre mientras el Event Trigger no ha declarado su cola, y se resuelve en cuanto arranca. Tratarlo como temporal es lo que hace que el evento espere en la outbox.
- Las consultas para monitorear la outbox deben separar pendientes (`published_at IS NULL AND failed_at IS NULL`), publicados y descartados (`failed_at IS NOT NULL`).

## ADR-028 — Modelo de programación de SendNotificationFunction (Fase 6)

**Estado:** Aceptada (Fase 6, entrega 6A).

### Contexto

SendNotificationFunction recibe `ItineraryCreatedEvent`, simula la notificación y guarda el historial. Debe seguir el modelo FaaS de la plataforma elegida (ADR-008) sin abandonar la arquitectura hexagonal del proyecto (ADR-002).

### Decisión

- **Modelo de Lambda:** la función es `handler(event, context)` en `app/handler.py`. La imagen la declara con `CMD ["app.handler.handler"]`.
- **Sin estado entre invocaciones:** no guarda datos de negocio en memoria. Lo único que se reutiliza es el *engine* de SQLAlchemy (el administrador de conexiones), creado la primera vez y conservado mientras el contenedor siga "caliente". Es la práctica que recomienda AWS para no abrir una conexión nueva en cada invocación.
- **Sin código de RabbitMQ:** la función recibe el evento ya extraído del mensaje. Leer la cola, confirmar (ACK) y reintentar es trabajo del Event Trigger (entrega 6B).
- **Arquitectura hexagonal dentro de la función:**

| Capa | Contenido |
|---|---|
| `domain` | `NotificationRecord`, `NotificationStatus` y la regla del destinatario (ADR-030) |
| `application` | `ItineraryCreatedEvent` (el evento tal como lo lee este consumidor), puertos `NotificationHistoryRepository`, `NotificationSender` y `UnitOfWork`, caso de uso `NotifyItineraryCreatedUseCase`, excepciones `InvalidEventError` y `TransientError` |
| `infrastructure` | `SimulatedEmailSender` (simula el correo con un log) y la persistencia con SQLAlchemy (ADR-029) |
| Adaptador de entrada | `app/handler.py` (el handler de Lambda) y `app/event_schema.py` (esquema Pydantic del contrato v1). Cumplen el papel de las rutas FastAPI en los servicios |

- **Validación del evento:** el esquema Pydantic comprueba el contrato v1 (ADR-020): `event_type = itinerary.created`, `event_version = 1`, UUID válidos, fechas con zona horaria, ids de aeropuerto y duración mayores que 0. Ignora los campos que no conoce (*Tolerant Reader*, igual que el Adapter de la Fase 1), para que un campo nuevo compatible no rompa al consumidor. La función **no importa código de Itinerary Service**: son contextos distintos y solo comparten el contrato publicado.
- **Respuesta de la función** (lo que recibe quien la invoca):

| `status` | Cuándo | Campos adicionales |
|---|---|---|
| `PROCESSED` | Se registró la notificación | `event_id`, `notification_id`, `notification_status` (`SENT` o `SKIPPED`) |
| `ALREADY_PROCESSED` | El `event_id` ya estaba en el historial (ADR-030) | `event_id` |
| `REJECTED` | El evento no cumple el contrato v1 (fallo permanente) | `event_id` (si se pudo leer) y `reason` |

- **Errores que lanza la función:** el RIE, igual que AWS Lambda, informa una excepción no capturada con un cuerpo `{"errorType": "<nombre de la clase>", "errorMessage": "..."}`.

| Situación | Qué hace la función | `errorType` |
|---|---|---|
| Evento inválido | No lanza excepción: responde `REJECTED` | — |
| PostgreSQL no disponible (sin conexión, timeout, conexión cortada) | Captura el error de SQLAlchemy y lanza `TransientError` | `TransientError` |
| Cualquier otro error (por ejemplo, un error de programación) | No lo captura | El nombre de su clase |

El Event Trigger (entrega 6B) usa ese `errorType` para distinguir un fallo de infraestructura de uno de otro tipo.

**Comportamiento comprobado del RIE (demostración de la 6A, 2026-11-10):**

- Un error de la función responde **HTTP 200**, igual que un éxito. El error solo se reconoce porque el cuerpo trae `errorType` (además de `errorMessage`, `requestId` y `stackTrace`); el RIE no agrega un header que lo marque. Por eso el trigger debe revisar el cuerpo y no solo el código HTTP.
- Con PostgreSQL detenido, la invocación responde en unos 2,6 s con `"errorType": "TransientError"`, dentro del timeout de la función (10 s).
- Si el cuerpo no es JSON, el runtime falla **antes** de llamar al handler con `"errorType": "Runtime.UnmarshalError"`. Por eso el trigger comprueba que el mensaje sea JSON antes de invocar la función.
- Al volver PostgreSQL, el mismo contenedor caliente se reconecta solo gracias a `pool_pre_ping` (ADR-029).

### Justificación

- El handler es delgado, como una ruta FastAPI: valida, llama al caso de uso y traduce el resultado. El caso de uso se prueba con *fakes* sin Lambda ni PostgreSQL.
- Responder `REJECTED` en lugar de lanzar una excepción hace explícito que el evento no sirve y que reintentarlo no lo arreglará.
- `TransientError` le da al trigger una señal estable para reconocer el fallo de infraestructura, sin que tenga que interpretar mensajes de error de PostgreSQL.

### Consecuencias

- Cambiar los nombres `PROCESSED`, `ALREADY_PROCESSED`, `REJECTED` o `TransientError` es un cambio de contrato con el Event Trigger.
- Si se olvida aplicar la migración, PostgreSQL responde "la tabla no existe". No es un error de conexión, así que **no** se informa como `TransientError` (ver ADR-029).

## ADR-029 — Historial de notificaciones en PostgreSQL propio (Fase 6)

**Estado:** Aceptada (Fase 6, entrega 6A). Resuelve la decisión pendiente sobre el almacenamiento del historial (ADR-004).

### Contexto

El historial de notificaciones necesita persistencia propia, separada de la base de itinerarios. También necesita una restricción de unicidad sobre `event_id` para la idempotencia (ADR-030).

### Decisión

- **Contenedor propio**, con el mismo patrón de ADR-016: `notification-postgres` (postgres:16-alpine) en el puerto **5434**, usuario y clave `notification` y base `notification_db`. Itinerary Service no lo conoce y la función no conoce la base de itinerarios.
- **Tabla `notification_history`** (una fila por `NotificationRecord`):

| Columna | Tipo | Significado |
|---|---|---|
| `id` | UUID, clave primaria | Identificador de la notificación |
| `event_id` | UUID, **único** (`uq_notification_history_event_id`) | `event_id` del evento recibido: clave de idempotencia |
| `itinerary_id` | UUID | Itinerario notificado (referencia por id, sin clave foránea: está en otra base) |
| `recipient` | VARCHAR(255), nulo | Correo del viajero; `NULL` si el itinerario no tiene correo |
| `channel` | VARCHAR(50) | `simulated-email` |
| `message` | TEXT | Texto de la notificación |
| `status` | VARCHAR(20), `CHECK` `SENT` o `SKIPPED` | Resultado (ADR-030) |
| `status_reason` | TEXT, nulo | Por qué no se envió (solo en `SKIPPED`) |
| `correlation_id` | VARCHAR(255), nulo | Correlation ID del evento, para seguir el flujo (Fase 9) |
| `processed_at` | TIMESTAMPTZ | Cuándo se procesó el evento |

- **Migraciones aparte, no en cada invocación:** Alembic vive en la carpeta de la función y se ejecuta desde su entorno virtual (`alembic upgrade head`), igual que en Itinerary Service. La imagen de la función **no incluye Alembic**:
  - `requirements.txt` tiene solo lo que va dentro de la función.
  - `requirements-dev.txt` agrega Alembic y pytest para el equipo.
  - En la Fase 10 la migración podrá correr como un contenedor de una sola ejecución.
- **Red Docker `notification-net`:** la función y `notification-postgres` se conectan por esta red. Dentro de un contenedor, `localhost` es el propio contenedor, así que la función usa `notification-postgres:5432`. Desde el equipo (Alembic y pruebas) se usa `localhost:5434`.
- **Conexión:** `connect_timeout` de 3 s (`DATABASE_CONNECT_TIMEOUT_SECONDS`) y `pool_pre_ping`. Este último comprueba la conexión guardada antes de usarla: si PostgreSQL se reinició mientras el contenedor estaba caliente, abre una nueva en lugar de fallar.

### Justificación

- PostgreSQL ya es conocido por el equipo y garantiza la unicidad de `event_id` con una restricción, que es la base de la idempotencia.
- Aplicar las migraciones en cada invocación haría más lenta cada ejecución y podría correr migraciones en paralelo si hubiera varias instancias. Las migraciones son una tarea de despliegue, no de la función.
- Una imagen sin herramientas de desarrollo es más pequeña y arranca más rápido (arranque en frío).

### Consecuencias

- Hay que aplicar la migración antes de la primera invocación. Si no se aplica, la función falla con un error que no es `TransientError` (ADR-028).
- Hasta la Fase 10 el contenedor y la red se crean a mano.

## ADR-030 — Idempotencia y destinatario de la notificación (Fase 6)

**Estado:** Aceptada (Fase 6, entrega 6A). Cambia los estados de `NotificationRecord` (sección 8.3 de `CLAUDE.md`).

### Contexto

La entrega es **al menos una vez** (ADR-025): el mismo evento puede llegar más de una vez. Además, `traveler_email` es opcional (ADR-018), así que hay itinerarios sin destinatario.

### Decisión

**Idempotencia.** *Idempotente* significa que procesar el mismo evento dos veces deja el mismo resultado que procesarlo una. El caso de uso sigue este orden dentro de una transacción:

1. Construye el `NotificationRecord`.
2. Lo inserta con `INSERT ... ON CONFLICT (event_id) DO NOTHING`. Si no se insertó, el evento ya estaba procesado: responde `ALREADY_PROCESSED` **sin volver a enviar** y sin duplicar el registro.
3. Si se insertó y hay destinatario, envía la notificación (simulada).
4. Hace `COMMIT` y responde `PROCESSED`.

**Por qué se inserta antes de enviar:** la restricción única "reserva" el `event_id`.

- Si llegan dos copias a la vez, la segunda espera a que termine la transacción de la primera, ve el conflicto y no envía nada.
- Si el envío falla, se hace rollback: no queda registro y el evento se puede reintentar.

**Destinatario** (regla del dominio, en `NotificationRecord.create`):

| Caso | `recipient` | `status` | `status_reason` |
|---|---|---|---|
| El evento trae `traveler_email` | El correo | `SENT` | `NULL` |
| `traveler_email` es `null` o vacío | `NULL` | `SKIPPED` | "El itinerario no tiene traveler_email: no hay destinatario para la notificación" |

`SKIPPED` **reemplaza a `FAILED`** de la sección 8.3. No tener correo no es un fallo, porque el correo es opcional por diseño. Y en esta fase nada produce `FAILED`: un envío que falla deshace la transacción y se reintenta, no se registra.

### Justificación

- La restricción única de PostgreSQL resuelve la idempotencia incluso con varias invocaciones en paralelo, sin bloqueos programados a mano.
- Registrar el caso sin correo deja constancia de que el evento sí se procesó y explica por qué no hubo envío.

### Consecuencias

- **Queda una ventana pequeña:** si el envío sale bien pero el `COMMIT` falla, el reintento envía otra vez. La notificación también es "al menos una vez". Para un correo simulado es aceptable; un proveedor real de correo se protegería enviando el `event_id` como su propia clave de idempotencia.
- Un `ALREADY_PROCESSED` es un éxito para quien invoca: el trigger debe confirmar (ACK) el mensaje.

## ADR-031 — Event Trigger: consumo, invocación y política de reintentos (Fase 6)

**Estado:** Aceptada (Fase 6, entrega 6B).

### Contexto

RabbitMQ no sabe invocar una función serverless, y la función no lee colas (ADR-028). Hace falta un componente que cumpla el papel del **Event Source Mapping** de AWS Lambda: leer la cola `notification.itinerary-created`, invocar SendNotificationFunction y decidir qué hacer con cada mensaje según la respuesta.

Como la entrega es "al menos una vez" y la función es idempotente (ADR-030), reintentar nunca duplica una notificación. Lo que hay que decidir es **cuándo** reintentar y **cuándo** apartar el mensaje en la DLQ.

### Decisión

**Componente.** El Event Trigger es un proceso aparte (`python -m app.main` en `serverless/event-trigger`):

- Consume con **ACK manual** y `prefetch_count=1`: RabbitMQ le entrega un mensaje a la vez y no le da el siguiente hasta que el trigger responde ACK, reject o nack del actual.
- Invoca la función con `POST` a la API de invocación del RIE (ADR-008), con el evento JSON como cuerpo y un timeout propio (`FUNCTION_TIMEOUT_SECONDS`, 15 s, mayor que los 10 s de la función).
- Si se pierde la conexión con RabbitMQ, espera y se reconecta, en lugar de terminar. Se detiene con Ctrl+C.

**Clasificación de la respuesta.** El RIE responde HTTP 200 también cuando la función falla (ADR-028), así que el trigger lee el código HTTP **y** el cuerpo:

| Respuesta de la invocación | Tipo de fallo | Acción |
|---|---|---|
| `status` = `PROCESSED` o `ALREADY_PROCESSED` | Ninguno | `basic_ack` |
| `status` = `REJECTED` | **Permanente** | `basic_reject(requeue=False)` → DLX → DLQ, sin reintentos |
| El mensaje no es JSON (no se invoca la función) | **Permanente** | `basic_reject(requeue=False)` → DLQ |
| Sin conexión con la función, timeout de la invocación, HTTP 5xx, `errorType` = `TransientError` o timeout de la propia función (el RIE responde HTTP 200 con el texto `Task timed out after N seconds`, comprobado en la 6B) | **Infraestructura** (temporal) | Reintentos con espera dentro del trigger. Si se agotan, espera `TRIGGER_REQUEUE_DELAY_SECONDS` y `basic_nack(requeue=True)`: el mensaje vuelve a la cola y se intenta otra vez. **Sin límite y nunca a la DLQ** |
| Cualquier otro `errorType`, un código HTTP inesperado o una respuesta que no se entiende | **Error de la función** (probablemente de programación) | Reintentos limitados con espera. Si se agotan, `basic_reject(requeue=False)` → DLQ |

**Valores por defecto** (variables de entorno, ver `.env.example`):

| Variable | Valor | Significado |
|---|---|---|
| `TRIGGER_INFRASTRUCTURE_ATTEMPTS` | 3 | Intentos por entrega ante un fallo de infraestructura, antes de devolver el mensaje a la cola |
| `TRIGGER_FUNCTION_ERROR_ATTEMPTS` | 3 | Intentos ante un error de la función, antes de enviarlo a la DLQ |
| `TRIGGER_RETRY_BACKOFF_SECONDS` | 1 | Espera inicial entre intentos; se duplica en cada intento (1 s, 2 s, 4 s…) |
| `TRIGGER_RETRY_MAX_BACKOFF_SECONDS` | 8 | Máximo de esa espera |
| `TRIGGER_REQUEUE_DELAY_SECONDS` | 10 | Pausa antes de devolver el mensaje a la cola, para no reintentar sin descanso |

**Capas.** El trigger no tiene reglas de negocio, así que no tiene capa de dominio:

| Capa | Contenido |
|---|---|
| `application` | `DeliveryHandler` (la política: de la respuesta a ACK, reject o requeue), `RetryPolicy`, el puerto `FunctionInvoker` y los tipos `InvocationResult` y `Decision`. Se prueba con fakes, sin RabbitMQ ni la función |
| `infrastructure` | `LambdaFunctionInvoker` (cliente HTTP con httpx que clasifica la respuesta del RIE), el consumidor de RabbitMQ con pika y la declaración de la topología (ADR-032) |
| `app/main.py` | Ensamblaje, bucle de reconexión y parada con Ctrl+C |

Las esperas usan `connection.sleep()` de pika, no `time.sleep()`. Mientras espera, pika sigue atendiendo los *heartbeats* (señales periódicas con las que RabbitMQ comprueba que el cliente sigue vivo), así RabbitMQ no cierra la conexión durante una pausa larga.

### Relación con ADR-027

Es el **mismo criterio de fallo temporal vs. permanente** que el Outbox Relay aplica en el productor, ahora en el consumidor:

| | Outbox Relay (productor, ADR-027) | Event Trigger (consumidor, esta decisión) |
|---|---|---|
| Fallo temporal | RabbitMQ no disponible (`EventPublishError`) | La función o su base de datos no disponibles (sin conexión, timeout, 5xx, `TransientError`) |
| Qué se hace | Sigue pendiente, se reintenta **sin límite** | Vuelve a la cola, se reintenta **sin límite** |
| Fallo permanente | Mensaje venenoso (payload ilegible, `event_type` desconocido) | Mensaje que no es JSON o que la función rechaza (`REJECTED`) |
| Qué se hace | `failed_at`: se aparta sin reintentar | DLQ: se aparta sin reintentar |
| Por qué | Un fallo temporal se arregla solo cuando vuelve la dependencia: descartar sería perder el evento. Un fallo permanente no se arregla reintentando y bloquearía a los demás | Lo mismo |

Hay un caso que el relay no tiene: un **error de la función que no es de infraestructura**. No se sabe si es temporal, así que recibe unos pocos reintentos y después va a la DLQ. Con `prefetch_count=1`, un mensaje que falla siempre bloquearía la cola para todos los demás si se reintentara sin límite.

### Justificación

- Reintentar sin límite los fallos de infraestructura evita llenar la DLQ con mensajes sanos cuando la función o PostgreSQL están caídos un rato. Cuando vuelven, los mensajes se procesan solos.
- Los reintentos dentro del trigger cubren cortes de pocos segundos sin devolver el mensaje. La pausa antes de `nack` evita un bucle que consuma CPU y llene el log mientras la dependencia sigue caída.
- La idempotencia de la función (ADR-030) hace seguro reintentar: un mensaje procesado cuya confirmación se perdió responde `ALREADY_PROCESSED` y recibe ACK.

### Consecuencias

- Mientras la función o su base de datos estén caídas, el mensaje vuelve una y otra vez al **inicio** de la cola y los que vienen detrás esperan. Es aceptable, porque fallarían igual por la misma causa.
- Un error de programación en la función manda a la DLQ cada mensaje que lo provoque, después de 3 intentos. Corregida la función, esos mensajes se devuelven a la cola con el comando de reprocesamiento (ver más abajo).
- El nombre `TransientError` y los estados de la respuesta son parte del contrato entre la función y el trigger (ADR-028).
- En AWS, el Event Source Mapping de Amazon MQ cumpliría este papel y no haría falta el trigger. Su política de reintentos se configura en la plataforma, no en código.

### Reprocesamiento de la DLQ (agregado en la entrega 6C)

Un mensaje **válido** también puede terminar en la DLQ por un problema de despliegue. Por ejemplo, si falta la migración del historial, PostgreSQL responde "la tabla no existe": no es un `TransientError` (ADR-028), así que es un error de la función y va a la DLQ tras 3 intentos. Lo mismo pasa con una imagen de la función rota. Corregido el problema, esos mensajes deben volver a procesarse.

**Comando** (desde `serverless/event-trigger`):

```
python -m app.replay_dlq          # mueve UN mensaje (el más antiguo)
python -m app.replay_dlq --all    # mueve todos los que hay en la DLQ al empezar
```

**Cómo mueve cada mensaje (`DeadLetterReplayer`), de uno en uno:**

1. Lo toma de la DLQ sin confirmarlo (`basic_get` con ACK manual).
2. Lo publica **directamente en la cola principal**: exchange por defecto (`""`) con la routing key igual al nombre de la cola. Así llega solo a `notification.itinerary-created`, aunque en el futuro haya otros consumidores enlazados a `itinerary.events`. Si se publicara en el exchange, les llegaría una copia repetida a todos.
3. Espera la confirmación de RabbitMQ (publisher confirms y `mandatory=True`).
4. Recién entonces lo confirma (ACK) en la DLQ.

Si los pasos 2 o 3 fallan, devuelve el mensaje a la DLQ (`nack` con `requeue`): no se pierde. Si el proceso se cae entre los pasos 3 y 4, el mensaje queda en las dos colas; la función es idempotente, así que la segunda copia responde `ALREADY_PROCESSED`.

**Otros detalles:**

- Conserva `message_id`, `correlation_id`, `content_type` y el modo persistente.
- Quita los headers que RabbitMQ agregó al rechazarlo (`x-death`, `x-first-death-*`, `x-last-death-*`) y suma 1 al header `x-dlq-replays`, para saber cuántas veces se reprocesó.
- Registra en el log cada mensaje movido: `message_id`, motivo del rechazo y veces rechazado.
- Solo mueve los mensajes que había **al empezar**. Si el problema sigue y el trigger los vuelve a rechazar, regresan a la DLQ y el comando termina, sin un ciclo infinito.
- Declara la topología antes de empezar, así funciona aunque el trigger nunca haya arrancado. El trigger puede estar encendido (procesa los mensajes en cuanto llegan) o apagado (esperan en la cola).

**Binding adicional de la DLQ.** Un mensaje devuelto así que se rechaza otra vez llega a la DLX con la routing key `notification.itinerary-created`, no con `itinerary.created`. Por eso la DLQ tiene un **segundo binding** a la DLX con esa clave. Sin él, la DLX no tendría a dónde enviarlo y el mensaje **se perdería**: lo detectó una prueba de integración de la 6C. Agregar un binding no cambia los argumentos de la cola, así que no causa `PRECONDITION_FAILED` con la cola existente.

**Procedimiento.** Está en `serverless/event-trigger/README.md`:

1. Revisar el motivo en la DLQ (panel de RabbitMQ, header `x-death` y log del trigger).
2. Corregir la causa.
3. Mover **un** mensaje y comprobar que se procesa.
4. Mover el resto con `--all`.

Los mensajes que no cumplen el contrato (`REJECTED`) **no** deben reprocesarse: volverían a la DLQ.

## ADR-032 — Propiedad de la topología de RabbitMQ (Fase 6)

**Estado:** Aceptada (Fase 6, entrega 6B). Corrige ADR-021.

### Contexto

Desde la Fase 4, el publicador de Itinerary Service declaraba toda la topología: el exchange, la cola de notificaciones, su binding, la DLX y la DLQ (ADR-021). Era una medida provisional mientras no existía el consumidor. Con el Event Trigger, hay que decidir quién declara cada elemento.

### Decisión

Cada lado declara **lo que le pertenece**:

| Elemento | Quién lo declara | Por qué |
|---|---|---|
| Exchange `itinerary.events` (topic, durable) | El publicador de Itinerary Service **y** el Event Trigger | Es el contrato público del productor. El trigger también lo declara porque necesita que exista para enlazar su cola |
| Cola `notification.itinerary-created` (durable, `x-dead-letter-exchange: itinerary.events.dlx`) y su binding con `itinerary.created` | El Event Trigger | Es la cola de **este** consumidor |
| DLX `itinerary.events.dlx` (direct, durable) y DLQ `notification.itinerary-created.dlq` (durable) con sus bindings (`itinerary.created` y, desde la 6C, `notification.itinerary-created` para los mensajes reprocesados) | El Event Trigger | Reciben lo que **este** consumidor rechaza (ADR-031) |

- Las declaraciones son idempotentes y usan **los mismos argumentos de ADR-021**. Así no hay `PRECONDITION_FAILED` contra una cola que ya exista desde las fases anteriores.
- El trigger las declara cada vez que se conecta o reconecta, así no depende de que Itinerary Service haya arrancado antes.

### Qué pasa si el trigger nunca arrancó

1. La cola no existe, así que el exchange no tiene a quién entregar el mensaje.
2. Como el publicador usa `mandatory=True`, RabbitMQ devuelve el mensaje y pika lanza `UnroutableError`, que `RabbitMQEventPublisher` convierte en `EventPublishError`.
3. El Outbox Relay lo trata como **fallo temporal** (ADR-025 y ADR-027): suma un intento y el evento **sigue pendiente en la outbox**.
4. Cuando el trigger arranca y declara su cola, el siguiente ciclo del relay publica el evento y se procesa.

No se pierde nada, y el relay no necesita ningún cambio para esto.

### Justificación

- En publicación/suscripción, el productor no debería conocer las colas de sus consumidores. Si mañana se agrega un segundo consumidor (por ejemplo, un reporte), este declara su propia cola y el productor no cambia.
- El Transactional Outbox ya garantiza que un evento sin destino espera en lugar de perderse. La versión anterior declaraba la cola desde el productor justamente para evitar esa pérdida, y ya no hace falta.

### Consecuencias

- Archivos de las Fases 4 y 5 modificados en Itinerary Service:
  - `app/infrastructure/messaging/topology.py` deja solo el exchange (`declare_exchange`).
  - `RabbitMQEventPublisher` llama a `declare_exchange`.
  - Las pruebas con canal falso comprueban que el publicador ya no declara colas.
  - El fixture de integración `rabbitmq_channel` declara la cola como lo haría el consumidor.
  - Se agrega una prueba de integración: sin cola enlazada, el evento queda pendiente.
- Los argumentos de la cola existen ahora en un solo componente (el trigger). Si cambian, solo cambia el trigger; pero la cola ya creada en RabbitMQ conserva los anteriores y habría que borrarla antes (RabbitMQ no permite cambiar los argumentos de una cola existente).
- En la demostración, el orden de arranque deja de importar: el trigger puede arrancar antes o después de Itinerary Service.

## 2. Revisión de decisiones

Las decisiones pendientes deberán resolverse antes de implementar los componentes afectados.

Toda modificación de una decisión aceptada deberá incluir la razón del cambio y sus consecuencias.
