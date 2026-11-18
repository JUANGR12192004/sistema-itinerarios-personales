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

# PYTHONPATH: el paquete compartido libs/observability (ADR-040) es código Python puro y sin
# dependencias propias: se copia y se pone en el PYTHONPATH, sin instalarlo con pip.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/libs/observability

WORKDIR /app/serverless/event-trigger

# requirements-lock.txt: todas las dependencias de ejecución (directas y transitivas) con versión
# exacta y hash SHA-256, generado a partir de requirements-runtime.txt.
# --require-hashes: solo se instala lo verificado en el lock (regla S8544 de SonarCloud).
# --only-binary :all: solo paquetes ya compilados, sin scripts de instalación (regla S8541).
COPY serverless/event-trigger/requirements-lock.txt .
RUN pip install --only-binary :all: --require-hashes -r requirements-lock.txt

COPY libs/observability/observability /app/libs/observability/observability

COPY serverless/event-trigger/app ./app

RUN useradd --system --no-create-home appuser
USER appuser

# Solo el servidor de métricas (ADR-038): el trigger no recibe solicitudes, consume la cola.
EXPOSE 9102

CMD ["python", "-m", "app.main"]
