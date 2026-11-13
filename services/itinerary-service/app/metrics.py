"""Métricas de Prometheus para Itinerary Service (ADR-038, Fase 9C).

Las métricas HTTP (HTTP_REQUESTS, HTTP_DURATION, metrics_app, metrics_middleware)
provienen del paquete compartido observability. Este módulo añade el contador de negocio
itineraries_created_total, específico de este servicio.

Las métricas del Outbox Relay (proceso aparte, puerto 9101) se definen en app/outbox_relay.py.
"""

from observability.metrics import HTTP_REQUESTS, HTTP_DURATION, metrics_app, metrics_middleware  # noqa: F401
from prometheus_client import Counter

ITINERARIES_CREATED = Counter(
    "itineraries_created_total",
    "Total de itinerarios de viaje creados exitosamente",
)
