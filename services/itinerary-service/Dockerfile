# Imagen de Itinerary Service (Fase 10).
#
# Una sola imagen, tres usos (en docker-compose.yml cambia solo el comando):
#   API              uvicorn app.main:app ...          (comando por defecto, puerto 8002)
#   Outbox Relay     python -m app.outbox_relay        (proceso aparte, ADR-025; métricas en 9101)
#   Migraciones      alembic upgrade head              (contenedor de una sola ejecución)
# Los tres comparten el mismo código y las mismas dependencias: construir una imagen por
# proceso duplicaría el build sin aportar nada.
#
# El contexto de build es la RAÍZ del repositorio (necesita libs/observability, ADR-040):
#   docker build -t itinerary-service -f services/itinerary-service/Dockerfile .
# El .dockerignore asociado es services/itinerary-service/Dockerfile.dockerignore.
FROM python:3.12-slim

# PYTHONPATH: el paquete compartido libs/observability (ADR-040) es código Python puro y sin
# dependencias propias: se copia y se pone en el PYTHONPATH, sin instalarlo con pip.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/libs/observability

WORKDIR /app/services/itinerary-service

# Solo dependencias de ejecución con versión fija (incluye Alembic para las migraciones), y solo
# paquetes ya compilados: pip no ejecuta scripts de instalación (reglas S8541 y S8544 de SonarCloud).
COPY services/itinerary-service/requirements-runtime.txt .
RUN pip install --only-binary :all: -r requirements-runtime.txt

COPY libs/observability/observability /app/libs/observability/observability

# Código de la aplicación y de las migraciones (alembic/env.py importa app.config y los modelos)
COPY services/itinerary-service/app ./app
COPY services/itinerary-service/alembic ./alembic
COPY services/itinerary-service/alembic.ini .

RUN useradd --system --no-create-home appuser
USER appuser

EXPOSE 8002 9101

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
