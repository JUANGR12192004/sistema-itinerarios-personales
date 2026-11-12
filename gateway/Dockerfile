# API Gateway (Fase 7, ADR-009): imagen oficial de Nginx + la plantilla de configuración.
# La imagen es multiarquitectura: arm64 (Mac con Apple Silicon) y amd64 (Windows y el CI).
FROM nginx:1.30.6-alpine

# Valores por defecto de la Fase 7 (servicios con uvicorn en el equipo).
# Se cambian con -e o --env-file al ejecutar el contenedor (ver .env.example),
# y en la Fase 10 desde Docker Compose con los nombres de los contenedores.
# NGINX_ENVSUBST_FILTER limita qué variables reemplaza la imagen en la plantilla:
# solo las que terminan en _UPSTREAM o empiezan por GATEWAY_.
ENV AIRPORT_SERVICE_UPSTREAM=host.docker.internal:8001 \
    ITINERARY_SERVICE_UPSTREAM=host.docker.internal:8002 \
    GATEWAY_PROXY_CONNECT_TIMEOUT=2s \
    GATEWAY_PROXY_READ_TIMEOUT=15s \
    NGINX_ENVSUBST_FILTER="_UPSTREAM\$|^GATEWAY_"

# Al arrancar, la imagen convierte templates/*.template en /etc/nginx/conf.d/*.conf.
COPY templates/ /etc/nginx/templates/

EXPOSE 8000
