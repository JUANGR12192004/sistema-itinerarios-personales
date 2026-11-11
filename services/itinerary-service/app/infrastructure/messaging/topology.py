"""Parte de la topología de RabbitMQ que pertenece a Itinerary Service (ADR-021 y ADR-032).

Topología = el conjunto de exchanges, colas y bindings (enlaces) por los que viaja un mensaje:

    Itinerary Service ──publica──▶ exchange "itinerary.events" (topic)   ← lo declara este servicio
                                      │ routing key "itinerary.created"
                                      ▼
                          cola "notification.itinerary-created"          ← la declara el Event Trigger
                                      │ si el consumidor rechaza el mensaje
                                      ▼
            exchange "itinerary.events.dlx" ──▶ cola "notification.itinerary-created.dlq"  ← Event Trigger

Cada lado declara lo que le pertenece (ADR-032): el productor, su exchange (su contrato
público); el consumidor, su cola, su binding y su DLQ. El productor no conoce las colas
de sus consumidores: un consumidor nuevo declara la suya sin cambiar este servicio.

Si ningún consumidor ha declarado su cola, el exchange no tiene a quién entregar el
mensaje: con `mandatory=True` RabbitMQ lo devuelve (UnroutableError), el publicador lanza
EventPublishError y el Outbox Relay deja el evento pendiente hasta que la cola exista.

La declaración es idempotente: declarar un exchange que ya existe con los mismos
argumentos no hace nada.
"""

from pika.adapters.blocking_connection import BlockingChannel

EXCHANGE = "itinerary.events"
ROUTING_KEY_ITINERARY_CREATED = "itinerary.created"


def declare_exchange(channel: BlockingChannel) -> None:
    """Declara el exchange de eventos de itinerarios (topic, durable: sobrevive a un reinicio)."""
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
