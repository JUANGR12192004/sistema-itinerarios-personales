# Imagen del Event Trigger (Fase 10).
#
# Equivalente local al Event Source Mapping de AWS (ADR-031): consume la cola de RabbitMQ
# e invoca SendNotificationFunction. La misma imagen sirve para reprocesar la DLQ:
#   docker compose run --rm event-trigger python -m app.replay_dlq --all
#
# El contexto de build es la RAÍZ del repositorio (necesita libs/observability, ADR-040):
#   docker build -t event-trigger -f serverless/event-trigger/Dockerfile .
# El .dockerignore asociado es serverless/event-trigger/Dockerfile.dockerignore.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Misma estructura del repositorio, para que "-e ../../libs/observability" funcione sin cambios.
WORKDIR /app/serverless/event-trigger

COPY libs/observability /app/libs/observability
COPY serverless/event-trigger/requirements.txt .
RUN pip install -r requirements.txt

COPY serverless/event-trigger/app ./app

RUN useradd --system --no-create-home appuser
USER appuser

# Solo el servidor de métricas (ADR-038): el trigger no recibe solicitudes, consume la cola.
EXPOSE 9102

CMD ["python", "-m", "app.main"]
