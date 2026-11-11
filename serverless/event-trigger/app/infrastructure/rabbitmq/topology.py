"""Topología de RabbitMQ que pertenece al Event Trigger (ADR-021 y ADR-032).

    Itinerary Service ──publica──▶ exchange "itinerary.events" (topic)   ← productor y trigger
                                      │ routing key "itinerary.created"
                                      ▼
                          cola "notification.itinerary-created"          ← trigger
                                      │ si el trigger rechaza el mensaje (basic_reject sin reencolar)
                                      ▼
            exchange "itinerary.events.dlx" ──▶ cola "notification.itinerary-created.dlq"  ← trigger

El trigger es el dueño de su cola, su binding, la DLX y la DLQ. Declara también el exchange
porque necesita que exista para enlazar su cola, aunque Itinerary Service no haya arrancado.

Los argumentos son EXACTAMENTE los de ADR-021: RabbitMQ no permite redeclarar una cola
existente con otros argumentos (responde PRECONDITION_FAILED y cierra el canal). Todas las
declaraciones son idempotentes: se repiten en cada conexión sin efecto si ya existen.

Los nombres se agrupan en QueueTopology para que las pruebas de integración usen una copia
con nombres propios (y no toquen la cola real ni su DLQ). El trigger usa NOTIFICATION_TOPOLOGY.
"""

from dataclasses import dataclass

from pika.adapters.blocking_connection import BlockingChannel


@dataclass(frozen=True)
class QueueTopology:
    """Nombres de los elementos de la topología del consumidor."""

    exchange: str = "itinerary.events"
    routing_key: str = "itinerary.created"
    queue: str = "notification.itinerary-created"
    dead_letter_exchange: str = "itinerary.events.dlx"
    dead_letter_queue: str = "notification.itinerary-created.dlq"


NOTIFICATION_TOPOLOGY = QueueTopology()

EXCHANGE = NOTIFICATION_TOPOLOGY.exchange
ROUTING_KEY_ITINERARY_CREATED = NOTIFICATION_TOPOLOGY.routing_key
QUEUE_NOTIFICATIONS = NOTIFICATION_TOPOLOGY.queue
DEAD_LETTER_EXCHANGE = NOTIFICATION_TOPOLOGY.dead_letter_exchange
DEAD_LETTER_QUEUE = NOTIFICATION_TOPOLOGY.dead_letter_queue


def declare_topology(channel: BlockingChannel, topology: QueueTopology = NOTIFICATION_TOPOLOGY) -> None:
    """Declara exchanges, colas y bindings. Todo es durable: sobrevive a un reinicio de RabbitMQ."""
    channel.exchange_declare(exchange=topology.exchange, exchange_type="topic", durable=True)
    channel.exchange_declare(exchange=topology.dead_letter_exchange, exchange_type="direct", durable=True)

    # Primero la cola de mensajes fallidos, para que exista antes de que llegue el primero
    channel.queue_declare(queue=topology.dead_letter_queue, durable=True)
    channel.queue_bind(
        queue=topology.dead_letter_queue,
        exchange=topology.dead_letter_exchange,
        routing_key=topology.routing_key,
    )
    # Segundo binding, para los mensajes reprocesados desde la DLQ (python -m app.replay_dlq):
    # se devuelven con el exchange por defecto y la routing key = nombre de la cola. Si se
    # rechazan otra vez, RabbitMQ los envía a la DLX con ESA routing key; sin este binding,
    # la DLX no tendría a dónde enviarlos y se perderían.
    channel.queue_bind(
        queue=topology.dead_letter_queue,
        exchange=topology.dead_letter_exchange,
        routing_key=topology.queue,
    )

    # Cola principal: los mensajes rechazados se reenvían al DLX con su routing key original
    channel.queue_declare(
        queue=topology.queue,
        durable=True,
        arguments={"x-dead-letter-exchange": topology.dead_letter_exchange},
    )
    channel.queue_bind(
        queue=topology.queue,
        exchange=topology.exchange,
        routing_key=topology.routing_key,
    )
