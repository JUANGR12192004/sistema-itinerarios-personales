# API Gateway (Fase 7-9, ADR-009): imagen oficial de Nginx con módulo OTel (ADR-036).
# nginx:1.30.6-alpine-otel contiene ngx_otel_module.so como módulo dinámico.
# La imagen es multiarquitectura: arm64 (Mac con Apple Silicon) y amd64 (Windows y el CI).
FROM nginx:1.30.6-alpine-otel

# Valores por defecto de la Fase 7 (servicios con uvicorn en el equipo).
# Se cambian con -e o --env-file al ejecutar el contenedor (ver .env.example),
# y en la Fase 10 desde Docker Compose con los nombres de los contenedores.
# NGINX_ENVSUBST_FILTER limita qué variables reemplaza la imagen en la plantilla:
# solo las que terminan en _UPSTREAM, empiezan por GATEWAY_ u OTEL_.
ENV AIRPORT_SERVICE_UPSTREAM=host.docker.internal:8001 \
    ITINERARY_SERVICE_UPSTREAM=host.docker.internal:8002 \
    GATEWAY_PROXY_CONNECT_TIMEOUT=2s \
    GATEWAY_PROXY_READ_TIMEOUT=15s \
    GATEWAY_RATE_LIMIT=10r/s \
    GATEWAY_RATE_BURST=20 \
    OTEL_EXPORTER_OTLP_HOST=host.docker.internal \
    GATEWAY_OTEL_TRACE=on \
    NGINX_ENVSUBST_FILTER="_UPSTREAM\$|^GATEWAY_|^OTEL_"

# Desde la Fase 8 el contexto de build es la raíz del repositorio:
#   docker build -t api-gateway -f gateway/Dockerfile .
# El .dockerignore asociado es gateway/Dockerfile.dockerignore.
COPY gateway/templates/ /etc/nginx/templates/
COPY frontend/ /usr/share/nginx/html/

EXPOSE 8000
