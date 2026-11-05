"""Topología de RabbitMQ para los eventos de itinerarios (ADR-021).

Topología = el conjunto de exchanges, colas y bindings (enlaces) por los que viaja un mensaje:

    Itinerary Service ──publica──▶ exchange "itinerary.events" (topic)
                                      │ routing key "itinerary.created"
                                      ▼
                          cola "notification.itinerary-created"
                                      │ si el consumidor rechaza el mensaje
                                      ▼
            exchange "itinerary.events.dlx" ──▶ cola "notification.itinerary-created.dlq"

- Exchange: recibe los mensajes y decide a qué colas copiarlos según la routing key.
- Cola: guarda los mensajes hasta que un consumidor los procese.
- Dead letter exchange (DLX) y cola DLQ: reciben los mensajes que fallaron, para revisarlos
  sin bloquear la cola principal.

Todas las declaraciones son idempotentes: declarar algo que ya existe con los mismos
argumentos no hace nada. Por eso el publicador puede declararlas en cada publicación
mientras el consumidor de la Fase 6 no exista.
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
