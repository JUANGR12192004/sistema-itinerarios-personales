# Event Trigger

Puente entre RabbitMQ y SendNotificationFunction (Fase 6, ADR-031). Lee la cola `notification.itinerary-created`,
invoca la función con cada evento y, según la respuesta, confirma el mensaje, lo reintenta o lo envía a la DLQ.

Cumple el papel del **Event Source Mapping** de AWS Lambda: en FaaS la función no lee colas, la plataforma le entrega
los eventos. Sus equivalentes en otras plataformas son los **conectores** de OpenFaaS y las **Sources** de Knative.

| | |
|---|---|
| Comando | `python -m app.main` (se detiene con Ctrl+C) |
| Consumo | ACK manual y `prefetch_count=1`: un mensaje a la vez |
| Invocación | `POST` al RIE de la función: `http://localhost:9000/2015-03-31/functions/function/invocations` |
| Topología | Declara el exchange, su cola, el binding, la DLX y la DLQ cada vez que se conecta (ADR-032) |
| Reconexión | Si se pierde RabbitMQ, reintenta cada 5 s en lugar de terminar |
| Reprocesar la DLQ | `python -m app.replay_dlq` (uno) o `python -m app.replay_dlq --all` (todos) |

## Política de reintentos (ADR-031)

El RIE responde HTTP 200 también cuando la función falla, así que el trigger lee el código HTTP **y** el cuerpo:

| Respuesta | Tipo | Acción |
|---|---|---|
| `PROCESSED` o `ALREADY_PROCESSED` | Éxito | `basic_ack` |
| `REJECTED`, o el mensaje no es JSON (sin invocar la función) | Permanente | `basic_reject(requeue=False)` → DLQ, sin reintentos |
| Sin conexión, timeout de la invocación, HTTP 5xx, `errorType` `TransientError` o `Task timed out` | Infraestructura | 3 intentos (esperas de 1 s y 2 s); después pausa de 10 s y `basic_nack(requeue=True)`. **Sin límite y nunca a la DLQ** |
| Otro `errorType` o una respuesta desconocida | Error de la función | 3 intentos; después `basic_reject(requeue=False)` → DLQ, para no bloquear la cola |

Es el mismo criterio de fallo temporal vs. permanente que el Outbox Relay aplica en el productor (ADR-027): lo
temporal se reintenta sin límite y lo permanente se aparta.

| Capa | Archivo | Qué hace |
|---|---|---|
| `application` | `delivery_handler.py` | `DeliveryHandler` y `RetryPolicy`: de la respuesta a `ACK`, `REJECT` o `REQUEUE`. Se prueba sin RabbitMQ ni la función |
| `application` | `invocation.py`, `ports.py` | Los cuatro resultados de una invocación y el puerto `FunctionInvoker` |
| `infrastructure` | `lambda_invoker.py` | Invoca la función con httpx y clasifica la respuesta |
| `infrastructure/rabbitmq` | `consumer.py`, `topology.py`, `dlq_replayer.py` | Consumidor pika, declaración de la topología y reprocesamiento de la DLQ |
| — | `main.py`, `replay_dlq.py` | Los dos comandos: el trigger y el reprocesamiento |

## Orden de arranque del sistema completo

El trigger es el **último** paso del orden completo, explicado en el [README raíz](../../README.md#orden-de-arranque):

1. Contenedores (`itinerary-postgres`, `itinerary-rabbitmq`, `notification-postgres` y la red `notification-net`).
2. Migraciones: `itinerary_db` y `notification_db`.
3. SendNotificationFunction (contenedor `send-notification-function`).
4. Airport Service.
5. Itinerary Service.
6. Outbox Relay.
7. **Event Trigger**.

Qué pasa si el trigger o lo que necesita no está:

| Situación | Consecuencia |
|---|---|
| El trigger **nunca** arrancó | La cola no existe: RabbitMQ devuelve el mensaje al relay (`UnroutableError`) y el evento **espera en la outbox**. Al arrancar el trigger, el relay lo publica en el siguiente ciclo |
| El trigger arrancó alguna vez y ahora está apagado | La cola existe: los mensajes se acumulan en ella (*Ready*) hasta que vuelva |
| RabbitMQ apagado | El trigger registra `Sin conexión con RabbitMQ` y reintenta cada 5 s |
| La función o `notification-postgres` apagados | Reintentos sin límite; los mensajes quedan *Unacked* o *Ready*, nunca en la DLQ |
| Falta la migración de `notification_db` | Los mensajes van a la DLQ tras 3 intentos: aplicar la migración y reprocesar la DLQ (más abajo) |

## Instalación (una vez)

Desde `serverless\event-trigger` (`serverless/event-trigger` en macOS).

**PowerShell:**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

**CMD:**

```cmd
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

**macOS (zsh):**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

## Ejecución

Con el entorno virtual activado (igual en PowerShell, CMD y zsh):

```
python -m app.main
```

Resultado esperado:

```
INFO [__main__] Event Trigger iniciado; invoca la función en http://localhost:9000/2015-03-31/functions/function/invocations
INFO [app.infrastructure.rabbitmq.consumer] Event Trigger conectado a localhost:5672; escuchando la cola notification.itinerary-created
INFO [app.application.delivery_handler] Evento procesado (PROCESSED): event_id=<id>. ACK
```

Se detiene con **Ctrl+C** (`Event Trigger detenido (Ctrl+C)`). Si en ese momento procesaba un mensaje, el mensaje
no recibió respuesta y RabbitMQ lo devuelve a la cola: no se pierde.

## Reprocesar la DLQ

Un mensaje **válido** puede terminar en la DLQ por un problema de despliegue. Por ejemplo, la migración del historial
sin aplicar o una imagen de la función con un error que el RIE informa con un `errorType` distinto de `TransientError`.
Una vez corregido el problema, el comando `app.replay_dlq` devuelve esos mensajes a la cola principal.

**Procedimiento** (con el entorno virtual activado, igual en PowerShell, CMD y zsh):

1. **Ver qué hay y por qué.** En el panel de RabbitMQ (http://localhost:15672, usuario y clave `guest`), abrir
   *Queues and Streams* → `notification.itinerary-created.dlq` → **Get messages**, con *Ack mode: Nack message
   requeue true*, para verlos sin sacarlos. El header `x-death` dice de qué cola vinieron y el motivo (`rejected`). El
   log del trigger dice por qué los rechazó: `La función rechazó el evento` (contrato) o `Error de la función en 3
   intentos` (despliegue).
2. **Corregir la causa.** Por ejemplo, `alembic upgrade head` en `serverless\send-notification-function`, o
   reconstruir la imagen de la función. Los mensajes rechazados por la función (`REJECTED`) **no** deben
   reprocesarse: no cumplen el contrato y volverían a la DLQ.
3. **Mover un mensaje y comprobar** que el trigger lo procesa (`Evento procesado ... ACK`):

   ```
   python -m app.replay_dlq
   ```

4. **Mover el resto:**

   ```
   python -m app.replay_dlq --all
   ```

Resultado esperado (uno por mensaje):

```
INFO [...dlq_replayer] Mensaje devuelto de la DLQ a la cola notification.itinerary-created: message_id=<event_id> motivo del rechazo=rejected veces rechazado=1 reprocesos=1
INFO [__main__] Reprocesamiento terminado: 1 mensaje(s) devuelto(s) a notification.itinerary-created; quedan 0 en la DLQ
```

Cómo funciona (ADR-031):

- Mueve los mensajes **de uno en uno**. Publica cada uno directamente en la cola (exchange por defecto), espera la
  confirmación de RabbitMQ y recién entonces lo borra de la DLQ. Si RabbitMQ no lo acepta, queda en la DLQ.
- Quita el header `x-death` del rechazo anterior y suma 1 al header `x-dlq-replays`.
- Solo mueve los mensajes que había **al empezar**. Si el problema sigue, el trigger los vuelve a rechazar y regresan
  a la DLQ, sin crear un ciclo infinito.
- El trigger puede estar encendido (procesa los mensajes en cuanto llegan) o apagado (esperan en la cola).

## Ver las colas en el panel de RabbitMQ

http://localhost:15672 (usuario y clave `guest`) → **Queues and Streams**:

| Cola | Columnas | Qué significan |
|---|---|---|
| `notification.itinerary-created` | *Ready* | Mensajes esperando al trigger |
| | *Unacked* | El mensaje que el trigger está procesando o reintentando (con la función caída verás 1 aquí) |
| | *Consumers* | 1 si el trigger está conectado |
| `notification.itinerary-created.dlq` | *Ready* | Mensajes apartados por un fallo permanente o un error de la función |

Si la cola principal no aparece, el trigger nunca la declaró: los eventos esperan en la outbox de Itinerary Service.

## Variables de entorno

| Variable | Por defecto | Descripción |
|---|---|---|
| `RABBITMQ_URL` | `amqp://localhost:5672/%2F` | Conexión a RabbitMQ (`guest/guest` si la URL no trae usuario) |
| `RABBITMQ_TIMEOUT_SECONDS` | `3.0` | Espera máxima para conectar |
| `RABBITMQ_RECONNECT_DELAY_SECONDS` | `5.0` | Pausa antes de reconectar |
| `FUNCTION_INVOKE_URL` | `http://localhost:9000/2015-03-31/functions/function/invocations` | API de invocación de la función |
| `FUNCTION_TIMEOUT_SECONDS` | `15.0` | Espera máxima de una invocación (mayor que los 10 s de la función) |
| `TRIGGER_INFRASTRUCTURE_ATTEMPTS` | `3` | Intentos ante un fallo de infraestructura antes de devolver el mensaje a la cola |
| `TRIGGER_FUNCTION_ERROR_ATTEMPTS` | `3` | Intentos ante un error de la función antes de enviarlo a la DLQ |
| `TRIGGER_RETRY_BACKOFF_SECONDS` | `1.0` | Espera inicial entre intentos; se duplica en cada intento |
| `TRIGGER_RETRY_MAX_BACKOFF_SECONDS` | `8.0` | Máximo de esa espera |
| `TRIGGER_REQUEUE_DELAY_SECONDS` | `10.0` | Pausa antes de devolver el mensaje a la cola |
| `LOG_LEVEL` | `INFO` | Nivel de log |

## Pruebas

Con el entorno virtual activado (igual en PowerShell, CMD y zsh):

```
pytest -v
```

Resultado esperado: todas pasan con RabbitMQ y la función encendidos; sin ellos, las de integración quedan SKIPPED.

**Las pruebas de integración no tocan las colas reales.** Cada prueba declara su propia topología con nombres únicos
(`test-<id>.itinerary.events`, `test-<id>.notification.itinerary-created`…), con los mismos argumentos que la real,
y la borra al terminar. Se pueden correr durante una demostración sin vaciar ni consumir los mensajes de
`notification.itinerary-created` ni de su DLQ. Únicas excepciones, documentadas en las pruebas:

- `test_la_topologia_real_es_compatible_con_la_que_ya_existe` redeclara la topología real para comprobar que no
  causa `PRECONDITION_FAILED`. No cambia sus mensajes, y si la cola real no existe **se omite**, para no crearla
  (eso alteraría el escenario "trigger apagado desde el principio").
- Las pruebas con la función real **agregan** filas al historial de notificaciones, con `event_id` nuevos.

Los archivos de `demo\` sirven para la demostración de punta a punta del [README raíz](../../README.md#demostración-de-punta-a-punta):
crear un itinerario y publicar a mano un evento inválido y un mensaje que no es JSON.

## Posibles errores

| Síntoma | Causa | Solución |
|---|---|---|
| `PRECONDITION_FAILED` al arrancar | La cola existe con otros argumentos | Borrarla vacía (`docker exec itinerary-rabbitmq rabbitmqctl delete_queue notification.itinerary-created`) y dejar que el trigger la cree |
| Reintentos con `ConnectError` sin parar | La función no está en el puerto 9000 | `docker ps`; `docker start send-notification-function` |
| `Sin conexión con RabbitMQ` cada 5 s | RabbitMQ apagado o arrancando | `docker start itinerary-rabbitmq` y esperar |
| Mensajes que nadie procesa | Dos triggers abiertos a la vez | Dejar uno solo |
| `DeprecationWarning ... utcfromtimestamp` en las pruebas | Viene de pika 1.3.2 al leer `x-death` | Conocida y anotada para la Fase 11 (CLAUDE.md, sección 9.3); no afecta |

## Estructura

```
app/
  application/
    delivery_handler.py  → DeliveryHandler, RetryPolicy, Decision (la política)
    invocation.py        → InvocationOutcome, InvocationResult
    ports.py             → FunctionInvoker
  infrastructure/
    lambda_invoker.py    → cliente HTTP del RIE y clasificación de la respuesta
    rabbitmq/
      consumer.py        → consumidor pika (ACK manual, prefetch 1)
      topology.py        → QueueTopology y declaración de la topología del consumidor
      dlq_replayer.py    → reprocesamiento de la DLQ
  config.py
  main.py                → python -m app.main
  replay_dlq.py          → python -m app.replay_dlq [--all]
demo/                    → itinerario de ejemplo, evento inválido y mensaje no JSON
tests/                   → política, cliente HTTP, consumidor, reprocesamiento, AsyncAPI e integración aislada
```
