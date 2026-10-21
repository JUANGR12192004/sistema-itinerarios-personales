
# 02. Arquitectura del sistema

## 1. Estilo arquitectónico

El sistema combinará tres enfoques:

1. **Microservicios:** servicios independientes, con responsabilidades delimitadas.
2. **Arquitectura basada en eventos:** comunicación asíncrona para reaccionar a la creación de itinerarios.
3. **Serverless:** ejecución de SendNotificationFunction como una función activada por eventos.

La arquitectura hexagonal se aplicará dentro de los servicios que necesiten separar las reglas de negocio de los mecanismos externos.

DDD se utilizará como guía para definir los límites del dominio y establecer un lenguaje común.

## 2. Componentes principales

### 2.1. Airport Service

Responsabilidades:

- Consultar información de aeropuertos mediante API Colombia.
- Exponer endpoints REST.
- Definir un puerto de salida para consultar proveedores de aeropuertos.
- Implementar un Adapter para la API externa.
- Transformar respuestas externas al modelo interno.
- Permitir consultas por identificador.
- Preparar datos para la visualización en el mapa.
- Incorporar Redis, timeout, retry y circuit breaker en la fase de resiliencia.

Airport Service será propietario de la integración con API Colombia.

El dominio no dependerá directamente de las estructuras de respuesta de esa API.

### 2.2. Itinerary Service

Responsabilidades:

- Crear, consultar, actualizar y eliminar itinerarios.
- Aplicar las reglas de negocio del dominio de itinerarios.
- Validar aeropuertos mediante HTTP hacia Airport Service.
- Persistir itinerarios en su propia base de datos PostgreSQL.
- Gestionar sus migraciones mediante Alembic.
- Publicar el evento de integración de creación.
- Incorporar Transactional Outbox en la fase correspondiente.

### 2.3. Sistema de notificaciones

Responsabilidades:

- Recibir el evento de integración de creación de itinerarios.
- Procesar el evento de forma asíncrona.
- Invocar o activar SendNotificationFunction según la integración elegida.
- Simular el envío de una notificación.
- Registrar el historial de procesamiento.
- Gestionar fallos de procesamiento.

La tecnología concreta de persistencia del historial y el mecanismo exacto de activación de la función se definirán antes de su implementación.

### 2.4. SendNotificationFunction

Será la función serverless responsable de:

- Recibir el evento correspondiente.
- Validar y procesar su contenido.
- Simular el envío de la notificación.
- Registrar el resultado del procesamiento.
- Manejar errores.

La función no será responsable de administrar itinerarios ni de implementar sus reglas de negocio.

### 2.5. API Gateway / BFF

Responsabilidades:

- Actuar como punto de entrada del frontend.
- Enrutar solicitudes a los servicios internos.
- Evitar incorporar lógica de negocio.
- Preparar la incorporación de rate limiting y propagación de JWT.

La solución concreta de gateway se seleccionará antes de la fase de implementación correspondiente.

### 2.6. Frontend

Responsabilidades:

- Consultar los servicios internos.
- Mostrar aeropuertos mediante Plotly JS.
- Permitir la gestión de itinerarios.
- Presentar errores y resultados al usuario.

No consumirá directamente la API externa.

## 3. Comunicación entre componentes

### Comunicación síncrona

Se utilizará HTTP/REST cuando un componente necesite una respuesta inmediata.

Ejemplo:

Itinerary Service → Airport Service

El servicio de itinerarios consulta la existencia de los aeropuertos antes de guardar el itinerario.

### Comunicación asíncrona

Se utilizará RabbitMQ para transportar eventos de integración.

Ejemplo:

Itinerary Service → RabbitMQ → Sistema de notificaciones

El emisor no tendrá que esperar a que termine la simulación de la notificación para completar el procesamiento normal de su solicitud.

La entrega del evento requerirá mecanismos de confiabilidad y recuperación que se definirán en las fases de mensajería y Transactional Outbox.

## 4. Persistencia y propiedad de datos

### Base de datos de itinerarios

Itinerary Service será propietario de los itinerarios almacenados en su PostgreSQL.

### Base de datos o almacenamiento de notificaciones

El historial de notificaciones tendrá persistencia propia, separada de los datos de itinerarios. La tecnología concreta se decidirá durante la planificación de la fase de notificaciones.

### Aeropuertos

La fuente externa de información será API Colombia. La incorporación de Redis permitirá almacenar temporalmente resultados de consultas.

No se ha definido todavía una base de datos persistente propia para Airport Service.

## 5. Resiliencia

Airport Service incorporará progresivamente:

- Timeout: limita cuánto puede esperar una solicitud.
- Retry: permite repetir operaciones fallidas de forma controlada.
- Exponential Backoff: incrementa el intervalo entre reintentos.
- Circuit Breaker: evita insistir continuamente contra una dependencia que falla.
- Redis: reduce consultas repetidas a la API externa.
- Fallback: permite una respuesta alternativa cuando sea válida y segura.

Los reintentos se limitarán a operaciones apropiadas y no deben multiplicar innecesariamente la carga sobre el proveedor externo.

## 6. Observabilidad

La solución incluirá progresivamente:

- Logs estructurados en JSON.
- Correlation ID para relacionar solicitudes.
- trace_id y span_id.
- OpenTelemetry.
- Jaeger.
- Prometheus.
- Grafana.

Se buscará seguir una operación desde el frontend hasta los servicios, la base de datos y el procesamiento del evento.

## 7. Despliegue

Docker y Docker Compose facilitarán el entorno de desarrollo local.

La orquestación completa se construirá en su fase específica, cuando los componentes ya se hayan implementado y probado individualmente.

## 8. Principios de diseño

- Separación de responsabilidades.
- Bajo acoplamiento.
- Alta cohesión.
- Propiedad de datos por servicio.
- Contratos explícitos entre componentes.
- Adaptación de dependencias externas mediante puertos y adaptadores.
- Procesamiento asíncrono para operaciones desacopladas.
- Complejidad proporcional a las necesidades del proyecto.
