
# 09. Guía para la sustentación

Guion corto para presentar el sistema funcionando: qué preparar, en qué orden mostrarlo, qué decir, cómo repartirlo
entre los tres integrantes y cómo responder las preguntas probables. Los comandos de cada demostración están completos,
para las tres terminales, en [`08-demostraciones.md`](08-demostraciones.md); aquí se indica cuál usar en cada momento.

## 1. Preparación previa

### El día anterior

1. Actualizar `main` y comprobar que la fecha de viaje de `serverless/event-trigger/demo/create-itinerary.json`
   (`2026-12-15`) sigue en el futuro; si no, cambiarla por una fecha futura.
2. Levantar el sistema completo una vez (la primera construcción de las imágenes tarda varios minutos) y recorrer el
   guion entero de la sección 2, cronometrándolo.
3. Tener a mano las evidencias de [`docs/evidencias/`](evidencias/README.md): son el respaldo si algo falla en vivo.

### 30 minutos antes

Desde la raíz del repositorio (los comandos `docker` son iguales en PowerShell, CMD y zsh):

```bash
docker compose up -d --build --wait
```

```bash
docker compose ps
```

Comprobar que todo está sano:

| Qué | Cómo | Resultado esperado |
|---|---|---|
| Contenedores | `docker compose ps -a` | Migraciones `Exited (0)`; `airport-service`, `itinerary-service`, `api-gateway`, bases, RabbitMQ y Redis `(healthy)` |
| Gateway | <http://localhost:8000/health> | `{"status":"ok","service":"api-gateway"}` |
| API Colombia | Abrir <http://localhost:8000> (pestaña Aeropuertos) | "51 aeropuertos con ubicación en el mapa". Además deja la caché caliente |
| Prometheus | <http://localhost:9090/targets> | Los cuatro destinos `UP` |
| RabbitMQ | <http://localhost:15672> (`guest` / `guest`) | La cola `notification.itinerary-created` con 1 consumidor |

Dejar abiertas estas pestañas del navegador: frontend (8000), Swagger de Itinerary (8002/docs), panel de RabbitMQ
(15672), Jaeger (16686) y Grafana (3000, `admin` / `admin`, dashboard "Sistema de Itinerarios Personales"). Y dos
terminales: una en la raíz del repositorio y otra en `serverless/event-trigger` (los `curl` de las demostraciones usan
sus archivos `demo/`). En CMD, ejecutar antes `chcp 65001` para ver bien las tildes.

### Plan B: sin internet o con API Colombia caída

- **Si API Colombia falla durante la demostración**, no es un problema, es una oportunidad: Airport Service responde
  con la copia de respaldo de la caché (`X-Cache: STALE`). Es el fallback de la Fase 2 funcionando en vivo.
- **Si no hay internet desde el principio**, usar el simulador de API Colombia de las pruebas E2E. Tiene 5 aeropuertos
  (ids 1, 2, 5, 30 y 43, con los mismos defectos que la API real), así que el mapa muestra 4 y el itinerario de
  `demo/create-itinerary.json` (1 → 5) sigue siendo válido:

  ```bash
  docker compose -f docker-compose.yml -f docker-compose.e2e.yml up -d --wait
  ```

  ```bash
  docker compose restart api-gateway
  ```

  ```bash
  docker compose exec redis redis-cli FLUSHALL
  ```

  (El gateway se reinicia porque Airport Service se recreó con otra IP, ADR-041; la caché se vacía para no mezclar
  datos de las dos fuentes.)
- **Si Docker falla**, presentar con las evidencias de [`docs/evidencias/`](evidencias/README.md), que muestran cada paso
  del guion con datos reales.

## 2. Guion de la demostración

Unos 25 minutos. Si hay menos tiempo, los pasos marcados como *opcional* se cuentan con su evidencia.

| # | Tiempo | Qué se muestra | Quién |
|---|---|---|---|
| 1 | 2 min | Problema, objetivos y las tres arquitecturas | Integrante 1 |
| 2 | 4 min | Arquitectura: componentes, hexagonal, DDD, Adapter | Integrante 1 |
| 3 | 3 min | Frontend: mapa y CRUD | Integrante 3 |
| 4 | 4 min | El evento de punta a punta y la traza en Jaeger | Integrante 2 |
| 5 | 3 min | Transactional Outbox con RabbitMQ detenido | Integrante 2 |
| 6 | 3 min | Serverless, DLQ y reprocesamiento | Integrante 2 |
| 7 | 2 min | Resiliencia de Airport Service (*opcional*: con evidencias) | Integrante 1 |
| 8 | 2 min | API Gateway: correlation ID y rate limiting | Integrante 3 |
| 9 | 1 min | Observabilidad en Grafana | Integrante 3 |
| 10 | 1 min | Pruebas, CI y calidad | Integrante 3 |
| 11 | 1 min | Limitaciones, Claude Code y cierre | Integrante 1 |

### Paso 1. Problema y objetivos (2 min)

Mostrar el README (inicio). Qué decir:

- Planificar viajes entre aeropuertos colombianos: consultar aeropuertos de una API pública, crear itinerarios y
  avisar al viajero cuando se crea uno.
- Lo interesante no es el CRUD sino **cómo se integran tres arquitecturas en un mismo flujo**: microservicios (Airport
  e Itinerary), eventos (RabbitMQ) y serverless (la función de notificación).

### Paso 2. Arquitectura (4 min)

Mostrar el diagrama general del README y el diagrama de clases de Airport Service
([`05-diagramas.md`, sección 3.1](05-diagramas.md#31-airport-service-patrón-adapter-y-decorators)). Qué decir:

- Cada servicio tiene su base de datos (o ninguna, Airport solo usa caché) y se comunica por **REST o por eventos**,
  nunca entrando en el código ni en la base del otro.
- Por dentro, **hexagonal**: el dominio (`Itinerary`, `Airport`) no conoce FastAPI ni PostgreSQL; los casos de uso
  hablan con **puertos** y la infraestructura los implementa. Las flechas del diagrama de clases apuntan hacia el centro.
- **Adapter**: `AirportProvider` es el Target, `ApiColombiaAirportAdapter` el Adapter y el JSON de API Colombia el
  Adaptee. Además es una **capa anticorrupción**: API Colombia trae latitud y longitud intercambiadas en 51 de 52
  aeropuertos, `"N/A"` en los códigos faltantes y `0, 0` en uno en construcción; el mapper lo corrige antes de que
  llegue al dominio.
- **DDD**: tres contextos (Catálogo de Aeropuertos, Planificación de Itinerarios, Notificaciones). Entre contextos solo
  viajan identificadores y contratos: el itinerario guarda el *id* del aeropuerto.

### Paso 3. Frontend (3 min)

En <http://localhost:8000>:

1. Pestaña Aeropuertos: "51 aeropuertos" y un color por tipo. Señalar que, sin la corrección del mapper, los puntos
   aparecerían en el océano Antártico.
2. Pestaña Itinerarios: crear uno **con correo** (por ejemplo Ana Pérez, `ana@example.com`), editarlo y mostrar la
   tabla. Intentar uno con salida igual a llegada: el error 422 lo devuelve el dominio, no el frontend.

Qué decir: el frontend solo habla con el gateway, nunca con API Colombia; es HTML y JavaScript sin framework, servido
por el mismo Nginx.

### Paso 4. El evento de punta a punta (4 min)

Seguir [`08-demostraciones.md`, caso normal](08-demostraciones.md#1-caso-normal) con `X-Correlation-ID: demo-sustentacion`:

1. `curl` del `POST` por el gateway → 201.
2. Logs del relay y del trigger: `docker compose logs --since 1m outbox-relay event-trigger`.
3. La fila en `notification_history` con el mismo `correlation_id` (consulta del caso normal).
4. En Jaeger, buscar el servicio `api-gateway` y abrir la traza: **seis servicios en una sola traza**.

Qué decir: la respuesta 201 llega en milisegundos; la notificación ocurre después, sin que el usuario espere. El mismo
`correlation_id` que entró por el gateway aparece en la base de otro contexto: así se rastrea una solicitud.

### Paso 5. Transactional Outbox (3 min)

Seguir la demostración de [`services/itinerary-service/README.md`](../services/itinerary-service/README.md) o la
evidencia [06](evidencias/06-outbox-rabbitmq-detenido.txt):

1. `docker compose stop rabbitmq`.
2. Crear un itinerario → **201** igualmente.
3. `outbox_events`: el evento está pendiente (`published_at` vacío) y `attempts` sube.
4. `docker compose up -d --wait rabbitmq` → unos segundos después, publicado y en `notification_history`.

Qué decir: sin el Outbox, ese evento se habría perdido (problema de *double write*, Fase 4).

### Paso 6. Serverless y DLQ (3 min)

1. Publicar el evento inválido ([caso 4 de `08-demostraciones.md`](08-demostraciones.md#4-evento-inválido-en-la-dlq-no-se-reprocesa)).
2. En el panel de RabbitMQ: la DLQ tiene 1 mensaje; con *Get messages* se ve `x-death` con `reason: rejected`.
3. Contar (o mostrar, si hay tiempo) el reprocesamiento con `python -m app.replay_dlq`
   ([caso 3](08-demostraciones.md#3-evento-que-termina-en-la-dlq-y-su-reprocesamiento)).

Qué decir: por qué es FaaS (pregunta 1 de la sección 4) y la política del trigger: fallo permanente → DLQ sin
reintentos; fallo de infraestructura → reintentos sin límite, nunca a la DLQ.

### Paso 7. Resiliencia (2 min, *opcional*)

En Swagger de Airport (<http://localhost:8001/docs>) o con `curl -i http://localhost:8000/api/airports/1` dos veces:
`X-Cache: MISS` y luego `HIT`. Los escenarios de timeout, circuit breaker y fallback están en
[`services/airport-service/README.md`](../services/airport-service/README.md#demostración-de-los-escenarios); si no hay
tiempo, explicarlos con el [diagrama de resiliencia](05-diagramas.md#6-flujo-de-resiliencia-de-airport-service).

### Paso 8. API Gateway (2 min)

Mostrar la evidencia [03](evidencias/03-gateway-correlation-id.txt) (correlation ID reenviado y generado) y la
[04](evidencias/04-rate-limit-429.txt) (429 tras 21 solicitudes). Qué decir: el gateway enruta, limita y propaga
headers; **no** valida reglas de negocio.

### Paso 9. Observabilidad (1 min)

Grafana: itinerarios creados, notificaciones, mensajes en la DLQ (debe coincidir con RabbitMQ), latencias p50/p95/p99.

### Paso 10. Pruebas y calidad (1 min)

Evidencia [01](evidencias/01-pruebas.txt): **642 pruebas** en siete suites, sin fallos ni omitidas; pirámide de cinco
niveles (unitarias, integración, contrato, gateway y E2E). El CI las ejecuta en cada pull request y SonarCloud analiza
la calidad (evidencias [19](evidencias/19-sonarcloud.png) y [20](evidencias/20-github-actions.png)).

### Paso 11. Cierre (1 min)

Las limitaciones conocidas (sección 5), el uso de Claude Code (pregunta 10) y una frase final: el sistema sigue
funcionando aunque fallen RabbitMQ, API Colombia o la base de notificaciones, y ningún evento se pierde.

## 3. Reparto sugerido

Es una sugerencia: conviene ajustarla para que cada integrante presente las fases de las que fue responsable (figuran
en los milestones de GitHub).

| Integrante | Pasos | Temas que debe dominar para las preguntas |
|---|---|---|
| Integrante 1 (por ejemplo, Juan David Gutierrez Rincón) | 1, 2, 7 y 11 | Microservicios, hexagonal, DDD, Adapter y capa anticorrupción, resiliencia, decisiones (ADR) |
| Integrante 2 (por ejemplo, Santiago Chilito García) | 4, 5 y 6 | Eventos, RabbitMQ, Outbox, idempotencia, FaaS, Event Trigger, DLQ |
| Integrante 3 (por ejemplo, Gustavo Rincón Araujo) | 3, 8, 9 y 10 | Frontend, gateway, observabilidad, Docker Compose, pruebas y CI |

Quien no está presentando maneja el teclado y las pestañas, para que el que habla no pierda el hilo.

## 4. Preguntas probables

**1. ¿Por qué SendNotificationFunction es FaaS si corre en Docker?**
Porque el modelo de programación es FaaS: es un `handler(event, context)` sin estado, que se ejecuta una vez por
evento y no sabe que existe RabbitMQ. Corre en la imagen oficial de AWS Lambda con el Runtime Interface Emulator: la
misma imagen se despliega sin cambios en AWS Lambda. Docker es solo cómo se ejecuta en local (ADR-008, ADR-028).

**2. ¿Qué problema resuelve el Transactional Outbox?**
El *double write*: guardar en PostgreSQL y publicar en RabbitMQ son dos escrituras sin transacción común; si RabbitMQ
falla después del commit, el evento se pierde. Con el Outbox, el evento se guarda en la misma transacción que el
itinerario y el relay lo publica después, reintentando hasta lograrlo (ADR-006, ADR-026).

**3. ¿Por qué el gateway no tiene lógica de negocio?**
Porque las reglas ya viven en el dominio de cada servicio; copiarlas en el gateway crearía dos fuentes de verdad, y
un componente que comparten todos tendría que cambiar con cada regla nueva. El gateway solo enruta, limita, propaga
headers y responde sus propios errores (ADR-009).

**4. ¿Qué pasa con un mensaje que llega a la DLQ?**
Queda guardado, sin bloquear la cola principal, con el header `x-death` que dice de dónde vino y por qué. Si era un
error de la función (por ejemplo, una migración faltante), se corrige la causa y `python -m app.replay_dlq` lo devuelve
a la cola. Si el evento no cumple el contrato, no se reprocesa: volvería a fallar (ADR-031).

**5. ¿Por qué una base de datos por servicio?**
Para que cada servicio sea dueño de sus datos y pueda cambiar su esquema sin romper a otros. Si dos servicios
compartieran tablas, quedarían acoplados por la base aunque se hablaran por REST. En Docker Compose cada base está en
su propia red, así que los demás contenedores ni siquiera pueden conectarse (ADR-004, ADR-016, ADR-041).

**6. ¿Cuál es la diferencia entre un evento de dominio y uno de integración?**
El de dominio es un hecho interno de un contexto y puede cambiar libremente. El de integración es un contrato público
con otros contextos: tiene versión (`event_version`), solo expone lo que promete y un cambio incompatible exige una
versión nueva. `ItineraryCreatedEvent` es de integración y por eso vive en la capa de aplicación (ADR-020).

**7. ¿Qué hace el circuit breaker?**
Después de 3 consultas fallidas seguidas a API Colombia, "abre el circuito": durante 30 s no la llama y responde de
inmediato con la copia de respaldo o con 503. Así no se insiste contra un servicio caído ni se hace esperar al usuario.
Después deja pasar una consulta de prueba y, si funciona, se cierra (ADR-014).

**8. ¿Cómo se sigue una solicitud en Jaeger?**
El gateway inicia la traza y propaga el header W3C `traceparent` a los servicios. Itinerary Service lo guarda en
`outbox_events`, el relay lo restaura al publicar, viaja en los headers de RabbitMQ y el trigger lo pasa a la función.
Por eso los seis componentes aparecen en una sola traza, aunque el relay publique segundos después (ADR-035, ADR-037).

**9. ¿Por qué el Adapter? ¿Qué pasa si cambia la API externa?**
Para que el resto del servicio no dependa del formato de API Colombia. Si cambia (otro nombre de campo, otra URL), solo
cambian el DTO externo, el mapper y el Adapter; los casos de uso y el dominio no se tocan. Si cambia tanto que todos los
aeropuertos son inválidos, el servicio responde 502 en vez de datos corruptos (ADR-003).

**10. ¿Cómo usaron Claude Code?**
Como asistente de programación con reglas escritas en `CLAUDE.md`: trabajar por fases y entregas, explicar cada
concepto, pedir aprobación para decisiones y no cambiar nada sin explicarlo. Cada cambio lo revisó, aprobó y subió un
integrante, que es el autor del commit; las decisiones están registradas como ADR.

**11. ¿Encontraron algún error real gracias a las pruebas?**
Sí, uno de consistencia que solo aparecía a veces. La prueba E2E `test_crud_completo_por_el_gateway` borraba un
itinerario (204) y al consultarlo justo después a veces recibía 200 en lugar de 404. La causa: el commit de `PUT` y
`DELETE` estaba en la dependencia de FastAPI que abre la sesión, después del `yield`, y FastAPI ejecuta ese código
**después de enviar la respuesta**. El cliente recibía "borrado" antes de que la base lo confirmara. Las pruebas
unitarias no lo veían porque usan repositorios falsos; solo una prueba de punta a punta, con la base real y dos
solicitudes seguidas, podía detectarlo. La corrección: los casos de uso de actualizar y eliminar confirman con el
puerto `UnitOfWork` antes de devolver el resultado, igual que la creación, y una prueba nueva comprueba el orden
(commit antes de responder). Detalle en ADR-019 y en
[`10-historial-de-fases.md`](10-historial-de-fases.md#correcciones-posteriores-a-la-fase-12).

Otras que pueden salir:

- **¿Qué pasa si el mismo evento llega dos veces?** La entrega es "al menos una vez". La función inserta con
  `ON CONFLICT (event_id) DO NOTHING`: el segundo responde `ALREADY_PROCESSED` y no se envía otro correo (ADR-030).
- **¿Por qué la validación de aeropuertos es HTTP y la notificación un evento?** Para guardar el itinerario hace falta
  la respuesta de Airport Service (síncrono); la notificación puede ocurrir después y su fallo no debe impedir crear el
  itinerario (asíncrono).
- **¿Cómo escalaría?** Los servicios no guardan estado en memoria (salvo el circuit breaker, ver sección 5) y pueden
  tener varias réplicas; el relay admite varias copias gracias a `SKIP LOCKED`, y la función escalaría sola en AWS Lambda.

## 5. Limitaciones conocidas y cómo explicarlas

Están en el README ([Limitaciones conocidas](../README.md#limitaciones-conocidas)). La idea al explicarlas: son
decisiones conscientes, documentadas en un ADR, no errores olvidados.

| Limitación | Cómo explicarla |
|---|---|
| La función no escala sola ni se apaga en local (ADR-008) | "Es una limitación de la plataforma local, no del código. El Runtime Interface Emulator ejecuta un solo contenedor; la misma imagen en AWS Lambda sí escala y se apaga." |
| El gateway responde 502 si un servicio se recrea con otra IP, hasta reiniciarlo (ADR-041) | "Nginx resuelve los nombres al arrancar. Solo pasa al reconstruir un servicio con el sistema encendido; se resuelve con `docker compose restart api-gateway`. Cambiarlo exigía modificar el gateway y sus pruebas para un caso de desarrollo." |
| `GenerateItineraryReportFunction` no se implementó (ADR-043) | "Era opcional. `SendNotificationFunction` ya demuestra el modelo FaaS completo: evento, trigger, idempotencia y DLQ. Una segunda función seguiría el mismo molde." |
| La protección de `main` es un acuerdo del equipo, no una regla de GitHub | "Trabajamos con PR, una aprobación y el CI en verde; configurar la regla en GitHub depende del dueño del repositorio." |
| El circuit breaker vive en la memoria de cada proceso | "Con varias réplicas, cada una tendría su propio estado. Para una sola instancia es suficiente; con varias se podría guardar en Redis." |
