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
# PYTHONPATH: el paquete compartido libs/observability (ADR-040) es código Python puro y sin
# dependencias propias, así que basta con copiarlo y ponerlo en el PYTHONPATH: no se instala con pip.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/libs/observability

WORKDIR /app/services/airport-service

# Primero las dependencias y después el código: si solo cambia app/, Docker reutiliza
# la capa de "pip install" (caché de capas) y el build tarda segundos.
# - requirements-lock.txt: TODAS las dependencias de ejecución (directas y transitivas), cada una
#   con versión exacta y el hash SHA-256 de sus wheels. Se genera a partir de requirements-runtime.txt
#   (ver el README del servicio); pytest y respx no van en la imagen.
# - --require-hashes: pip rechaza cualquier paquete que no esté en el lock o cuyo archivo no coincida
#   con el hash: el build siempre instala exactamente lo verificado (regla S8544 de SonarCloud).
# - --only-binary :all: solo acepta paquetes ya compilados (wheels): pip no ejecuta scripts de
#   instalación de terceros durante el build (regla S8541 de SonarCloud).
COPY services/airport-service/requirements-lock.txt .
RUN pip install --only-binary :all: --require-hashes -r requirements-lock.txt

COPY libs/observability/observability /app/libs/observability/observability

COPY services/airport-service/app ./app

# Usuario sin privilegios: si alguien explota el servicio, no es root dentro del contenedor.
RUN useradd --system --no-create-home appuser
USER appuser

EXPOSE 8001

# --host 0.0.0.0: acepta conexiones de otros contenedores (con 127.0.0.1 solo desde dentro).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
