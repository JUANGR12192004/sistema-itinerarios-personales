# Imagen de Airport Service (Fase 10).
#
# El contexto de build es la RAÍZ del repositorio (como el gateway y la función, ADR-040),
# porque el servicio necesita el paquete compartido libs/observability:
#   docker build -t airport-service -f services/airport-service/Dockerfile .
# El .dockerignore asociado es services/airport-service/Dockerfile.dockerignore.
#
# La imagen base es multiarquitectura: arm64 (Mac con Apple Silicon) y amd64 (Windows y el CI).
FROM python:3.12-slim

# PYTHONDONTWRITEBYTECODE: no crear __pycache__ (el usuario del contenedor no puede escribir en /app).
# PYTHONUNBUFFERED: los logs JSON salen al instante en `docker compose logs`.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Se reproduce la estructura del repositorio para que la línea
# "-e ../../libs/observability" de requirements.txt funcione sin cambios:
#   /app/libs/observability
#   /app/services/airport-service   ← directorio de trabajo
WORKDIR /app/services/airport-service

# Primero las dependencias y después el código: si solo cambia app/, Docker reutiliza
# la capa de "pip install" (caché de capas) y el build tarda segundos.
COPY libs/observability /app/libs/observability
COPY services/airport-service/requirements.txt .
RUN pip install -r requirements.txt

COPY services/airport-service/app ./app

# Usuario sin privilegios: si alguien explota el servicio, no es root dentro del contenedor.
RUN useradd --system --no-create-home appuser
USER appuser

EXPOSE 8001

# --host 0.0.0.0: acepta conexiones de otros contenedores (con 127.0.0.1 solo desde dentro).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
