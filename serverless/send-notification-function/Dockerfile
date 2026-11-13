# Imagen de SendNotificationFunction (ADR-008).
#
# La imagen base oficial de AWS Lambda para Python 3.12 trae:
# - el cliente del runtime de Lambda (awslambdaric), que llama a nuestro handler;
# - el Runtime Interface Emulator (RIE), que en local hace el papel del servicio Lambda
#   y expone la API de invocación en el puerto 8080 del contenedor.
# La misma imagen se puede desplegar en AWS Lambda sin cambios.
#
# Desde la Fase 9 el contexto de build es la raíz del repositorio (igual que el gateway),
# porque la función necesita libs/observability. Comando de build:
#   docker build -t send-notification-function -f serverless/send-notification-function/Dockerfile .
FROM public.ecr.aws/lambda/python:3.12

# Paquete compartido de observabilidad (Microservice Chassis Pattern, Fase 9).
# Se instala antes de las dependencias de la función para que el caché de capas de Docker
# no se invalide cuando cambia el código de la función (app/).
COPY libs/ ${LAMBDA_TASK_ROOT}/libs/
RUN pip install --no-cache-dir "${LAMBDA_TASK_ROOT}/libs/observability" --target "${LAMBDA_TASK_ROOT}"

# Dependencias de la función (solo requirements.txt: Alembic y pytest no van en la imagen).
# psycopg[binary] incluye libpq, que la imagen de Lambda no trae (x86_64 y arm64).
COPY serverless/send-notification-function/requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r "${LAMBDA_TASK_ROOT}/requirements.txt" --target "${LAMBDA_TASK_ROOT}"

# Código de la función
COPY serverless/send-notification-function/app ${LAMBDA_TASK_ROOT}/app

# Timeout de la función en segundos. Solo lo usa el emulador local;
# en AWS el timeout se configura en la función.
ENV AWS_LAMBDA_FUNCTION_TIMEOUT=10

# Handler: módulo app/handler.py, función handler(event, context)
CMD ["app.handler.handler"]
