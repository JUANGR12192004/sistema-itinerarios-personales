
# 08. Demostraciones

> Este contenido estaba en el `README.md` raíz hasta la Fase 11 y se movió aquí en la Fase 12, sin cambios de fondo.
> Cómo levantar el sistema: [Instalación y ejecución](../README.md#instalación-y-ejecución) en el README raíz.
> El orden recomendado para la sustentación está en [`09-guia-sustentacion.md`](09-guia-sustentacion.md).

**Contenido:** [Demostración de punta a punta](#demostración-de-punta-a-punta) (caso normal, evento duplicado, DLQ y
reprocesamiento, evento inválido, ver las colas) · [Demostración de observabilidad](#demostración-de-observabilidad)
(Jaeger y Grafana)

Las demostraciones de cada componente por separado están en su README: escenarios de resiliencia y caché en
[`services/airport-service/README.md`](../services/airport-service/README.md), double write resuelto con el Outbox en
[`services/itinerary-service/README.md`](../services/itinerary-service/README.md), invocación directa de la función en
[`serverless/send-notification-function/README.md`](../serverless/send-notification-function/README.md), reintentos y
DLQ en [`serverless/event-trigger/README.md`](../serverless/event-trigger/README.md) y rate limiting y errores del
gateway en [`gateway/README.md`](../gateway/README.md).

## Demostración de punta a punta

Recorrido completo: **gateway** → crear un itinerario → outbox → relay → RabbitMQ → trigger → función → historial.
Requisitos: el sistema levantado con Docker Compose o con los nueve pasos del [arranque manual](07-ejecucion-manual.md).

> **Con Docker Compose** los contenedores tienen otros nombres (`sistema-itinerarios-<servicio>-1`), así que en los
> comandos de abajo se cambia:
>
> | Modo manual | Docker Compose |
> |---|---|
> | `docker exec notification-postgres ...` | `docker compose exec notification-postgres ...` |
> | `docker exec itinerary-postgres ...` | `docker compose exec itinerary-postgres ...` |
> | `docker logs api-gateway` / `docker logs send-notification-function` | `docker compose logs api-gateway` / `docker compose logs send-notification-function` |
> | Logs del relay y del trigger en su terminal | `docker compose logs -f outbox-relay event-trigger` |
> | `python -m app.replay_dlq` | `docker compose run --rm event-trigger python -m app.replay_dlq` |
>
> Los `curl` no cambian.

Las solicitudes entran por el gateway
(`http://localhost:8000/api/itineraries`), igual que las del frontend. Los comandos se ejecutan desde `serverless\event-trigger` y son **iguales en
PowerShell y CMD** (en CMD, ejecutar antes `chcp 65001` para ver bien las tildes). En la Terminal de macOS (zsh) los
`docker exec` y `python -m ...` son iguales; los `curl` tienen su propio bloque (`curl` en lugar de `curl.exe` y la
ruta del archivo con `/`). El cuerpo del itinerario está en `demo\create-itinerary.json`; si la fecha `2026-12-15` ya
pasó, cámbiala por una futura.

### 1. Caso normal

```
curl.exe -s -X POST http://localhost:8000/api/itineraries -H "Content-Type: application/json" -H "X-Correlation-ID: demo-e2e" --data-binary "@demo\create-itinerary.json"
```

**macOS (zsh):**

```bash
curl -s -X POST http://localhost:8000/api/itineraries -H "Content-Type: application/json" -H "X-Correlation-ID: demo-e2e" --data-binary "@demo/create-itinerary.json"
```

Resultado esperado:

- El gateway devuelve el **201** de Itinerary Service con el itinerario, y el header `X-Correlation-ID: demo-e2e`.
- `docker logs api-gateway` muestra la solicitud con `upstream_status=201 correlation_id=demo-e2e`.
- Unos segundos después, el log del relay muestra `1 publicados` y el del trigger,
  `Evento procesado (PROCESSED): event_id=<id>. ACK`.
- `docker logs send-notification-function` muestra `Correo simulado enviado a ana@example.com: Hola Ana Pérez...`.

El registro en el historial, con el mismo `correlation_id` que llegó al gateway (la trazabilidad empieza en el gateway):

```
docker exec notification-postgres psql -U notification -d notification_db -c "SELECT event_id, status, recipient, correlation_id, processed_at FROM notification_history ORDER BY processed_at DESC LIMIT 3;"
```

Y en la outbox, el evento ya publicado:

```
docker exec itinerary-postgres psql -U itinerary -d itinerary_db -c "SELECT id, published_at, attempts FROM outbox_events ORDER BY occurred_at DESC LIMIT 1;"
```

**Sin `X-Correlation-ID`:** repetir el `POST` sin ese header. El gateway genera uno con forma de UUID, lo devuelve en
el header `X-Correlation-ID` de la respuesta, y ese mismo valor aparece en el log del relay y en `notification_history`.

### 2. Evento duplicado

La entrega es "al menos una vez": si el relay se cae entre publicar y marcar `published_at`, publica el evento otra
vez. Se simula quitando la marca del último evento:

```
docker exec itinerary-postgres psql -U itinerary -d itinerary_db -c "UPDATE outbox_events SET published_at = NULL WHERE id = (SELECT id FROM outbox_events ORDER BY occurred_at DESC LIMIT 1);"
```

Resultado esperado:

- El relay lo publica otra vez y el trigger registra `Evento procesado (ALREADY_PROCESSED): event_id=<el mismo id>. ACK`.
- La consulta del historial sigue mostrando **una sola fila** para ese `event_id`: la función es idempotente.
- No hay un segundo correo simulado en los logs de la función.

### 3. Evento que termina en la DLQ y su reprocesamiento

Un evento válido termina en la DLQ cuando falla el despliegue. Se simula la **migración del historial sin aplicar**
renombrando la tabla, sin borrar su contenido:

```
docker exec notification-postgres psql -U notification -d notification_db -c "ALTER TABLE notification_history RENAME TO notification_history_respaldo;"
curl.exe -s -X POST http://localhost:8000/api/itineraries -H "Content-Type: application/json" -H "X-Correlation-ID: demo-dlq" --data-binary "@demo\create-itinerary.json"
```

**macOS (zsh):** el mismo `docker exec` y después:

```bash
curl -s -X POST http://localhost:8000/api/itineraries -H "Content-Type: application/json" -H "X-Correlation-ID: demo-dlq" --data-binary "@demo/create-itinerary.json"
```

Resultado esperado: el trigger hace 3 intentos con `errorType=ProgrammingError: ... relation "notification_history"
does not exist` y registra `Error de la función en 3 intentos ... Va a la DLQ`. En el panel
(http://localhost:15672 → *Queues and Streams*), `notification.itinerary-created.dlq` tiene 1 mensaje.

Ahora se **corrige la causa** (la tabla vuelve a existir) y se **reprocesa** el mensaje:

```
docker exec notification-postgres psql -U notification -d notification_db -c "ALTER TABLE notification_history_respaldo RENAME TO notification_history;"
python -m app.replay_dlq
```

Resultado esperado:

- El comando registra `Mensaje devuelto de la DLQ a la cola notification.itinerary-created: message_id=<event_id> motivo del rechazo=rejected ...`.
- El trigger registra `Evento procesado (PROCESSED) ... ACK`.
- La DLQ queda en 0 y el historial tiene la fila con `correlation_id = demo-dlq`.

### 4. Evento inválido en la DLQ (no se reprocesa)

Itinerary Service solo produce eventos válidos, así que se publica uno a mano con la API del panel de RabbitMQ:

```
curl.exe -s -u guest:guest -X POST http://localhost:15672/api/exchanges/%2F/itinerary.events/publish -H "Content-Type: application/json" --data-binary "@demo\publish-invalid-event.json"
```

**macOS (zsh):**

```bash
curl -s -u guest:guest -X POST http://localhost:15672/api/exchanges/%2F/itinerary.events/publish -H "Content-Type: application/json" --data-binary "@demo/publish-invalid-event.json"
```

Resultado esperado: el trigger registra `La función rechazó el evento (fallo permanente) ... Va a la DLQ`, sin
reintentos. Este mensaje **no** se reprocesa: no cumple el contrato y volvería a la DLQ. Con
`demo\publish-not-json.json` se ve el mismo resultado para un mensaje que no es JSON, sin que se invoque la función.

### Ver en qué cola está cada mensaje

En http://localhost:15672 (usuario y clave `guest`) → **Queues and Streams**:

- `notification.itinerary-created`: *Ready* (esperando al trigger), *Unacked* (procesándose o reintentándose) y
  *Consumers* (1 si el trigger está conectado).
- `notification.itinerary-created.dlq`: mensajes apartados. En **Get messages** con *Ack mode: Nack message requeue
  true* se ven sin sacarlos; el header `x-death` dice de qué cola vinieron y el motivo.

Más escenarios (función apagada, base de datos de notificaciones apagada, trigger apagado desde el principio) en
[`serverless/event-trigger/README.md`](../serverless/event-trigger/README.md) y en ADR-031.


## Demostración de observabilidad

Requisitos: el sistema levantado con Docker Compose (incluye Jaeger, Prometheus y Grafana), o los nueve pasos del
[arranque manual](07-ejecucion-manual.md) incluyendo el paso 2. Con Compose, el archivo del itinerario está en
`serverless\event-trigger\demo\create-itinerary.json`: ejecutar el `curl` desde `serverless\event-trigger`.

### Seguir una solicitud de punta a punta en Jaeger

```
curl.exe -s -X POST http://localhost:8000/api/itineraries -H "Content-Type: application/json" -H "X-Correlation-ID: demo-traza" --data-binary "@demo\create-itinerary.json"
```

**macOS (zsh):**

```bash
curl -s -X POST http://localhost:8000/api/itineraries -H "Content-Type: application/json" -H "X-Correlation-ID: demo-traza" --data-binary "@demo/create-itinerary.json"
```

Resultado esperado:

1. La solicitud devuelve 201.
2. En Jaeger (<http://localhost:16686>), buscar el servicio `api-gateway` → aparece la traza que conecta el gateway, Itinerary Service, Airport Service (dos llamadas de validación), la escritura en PostgreSQL y el contexto guardado en la outbox.
3. Unos segundos después, el relay publica el evento: en Jaeger aparece una traza del `itinerary-service-outbox-relay` que continúa el span original gracias al `traceparent` guardado en `outbox_events`.

### Ver métricas en Grafana

Abrir <http://localhost:3000> (usuario `admin`, clave `admin`), ir a **Dashboards → Sistema de Itinerarios Personales**.

- Crear varios itinerarios y observar que `itineraries_created_total` sube.
- El panel "Outbox Relay" muestra los eventos publicados en tiempo real.
- El panel "HTTP Latencia" muestra los percentiles p50, p95 y p99 de los últimos 5 minutos.

Los mismos datos en bruto están en Prometheus (<http://localhost:9090>): buscar `http_requests_total` o `itineraries_created_total`.

