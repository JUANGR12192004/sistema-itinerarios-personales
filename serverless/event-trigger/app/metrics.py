"""Métricas de Prometheus para el Event Trigger (ADR-038, Fase 9C).

Registra el resultado de cada invocación a SendNotificationFunction con
una etiqueta `outcome` que distingue los cuatro resultados posibles:
  - success: la función respondió PROCESSED o ALREADY_PROCESSED
  - rejected: la función rechazó el evento (fallo permanente → DLQ)
  - infrastructure_error: sin conexión, timeout o TransientError (se reintenta)
  - function_error: error inesperado de la función (se reintenta limitado → DLQ)

El proceso inicia un servidor HTTP en el puerto METRICS_PORT (9102 por defecto)
al arrancar para que Prometheus pueda consultar estas métricas.
"""

from prometheus_client import Counter

NOTIFICATIONS_DISPATCHED = Counter(
    "notifications_dispatched_total",
    "Total de invocaciones a SendNotificationFunction por resultado",
    ["outcome"],
)
