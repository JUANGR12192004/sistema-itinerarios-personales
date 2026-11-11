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
"""

from pika.adapters.blocking_connection import BlockingChannel

EXCHANGE = "itinerary.events"
ROUTING_KEY_ITINERARY_CREATED = "itinerary.created"
QUEUE_NOTIFICATIONS = "notification.itinerary-created"
DEAD_LETTER_EXCHANGE = "itinerary.events.dlx"
DEAD_LETTER_QUEUE = "notification.itinerary-created.dlq"


def declare_topology(channel: BlockingChannel) -> None:
    """Declara exchanges, colas y bindings. Todo es durable: sobrevive a un reinicio de RabbitMQ."""
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.exchange_declare(exchange=DEAD_LETTER_EXCHANGE, exchange_type="direct", durable=True)

    # Primero la cola de mensajes fallidos, para que exista antes de que llegue el primero
    channel.queue_declare(queue=DEAD_LETTER_QUEUE, durable=True)
    channel.queue_bind(
        queue=DEAD_LETTER_QUEUE,
        exchange=DEAD_LETTER_EXCHANGE,
        routing_key=ROUTING_KEY_ITINERARY_CREATED,
    )

    # Cola principal: los mensajes rechazados se reenvían al DLX con su routing key original
    channel.queue_declare(
        queue=QUEUE_NOTIFICATIONS,
        durable=True,
        arguments={"x-dead-letter-exchange": DEAD_LETTER_EXCHANGE},
    )
    channel.queue_bind(
        queue=QUEUE_NOTIFICATIONS,
        exchange=EXCHANGE,
        routing_key=ROUTING_KEY_ITINERARY_CREATED,
    )
