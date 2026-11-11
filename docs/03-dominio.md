
# 03. Dominio, DDD y contextos delimitados

## 1. Propósito

Definir los conceptos principales del negocio, sus responsabilidades y los límites iniciales de cada contexto.

Esta definición es preliminar y deberá validarse durante la implementación.

## 2. Dominio principal

El dominio principal es la planificación y gestión de itinerarios de viaje.

El sistema necesita identificar aeropuertos válidos, asociarlos a un itinerario y generar una notificación cuando se cree dicho itinerario.

## 3. Lenguaje ubicuo

Se utilizarán los siguientes términos de manera consistente. El código se escribe en inglés; la documentación, en español.

### 3.1. Términos del negocio

| Término del negocio | Código | Significado |
|---|---|---|
| Aeropuerto | `Airport` | Instalación de transporte aéreo identificada por un identificador y sus atributos disponibles. |
| Itinerario | `Itinerary` | Registro que representa un viaje planificado entre dos aeropuertos. |
| Viajero | `traveler_name` | Nombre de la persona que realiza el viaje; no puede estar vacío. |
| Correo del viajero | `traveler_email` | Correo electrónico opcional del viajero; lo usa la notificación simulada de la Fase 6. |
| Aeropuerto de salida | `departure_airport_id` | Referencia por ID al aeropuerto desde el que comienza el viaje. |
| Aeropuerto de llegada | `arrival_airport_id` | Referencia por ID al aeropuerto al que se dirige el viaje; distinto del de salida. |
| Fecha de viaje | `travel_date` | Fecha y hora de salida con zona horaria; no puede estar en el pasado al crear. |
| Duración | `duration_minutes` | Duración estimada del vuelo en minutos; mayor que cero. |
| Itinerario creado | `ItineraryCreatedEvent` | Hecho de negocio: se registró un nuevo itinerario. |
| Notificación | `NotificationRecord` | Registro de un aviso simulado asociado a un evento de creación. |
| Mensaje pendiente | `OutboxMessage` | Evento de integración guardado y pendiente de publicar. |

### 3.2. Términos técnicos y arquitectónicos

| Término | Definición |
|---|---|
| Airport Service | Servicio responsable de consultar y normalizar información de aeropuertos. |
| Itinerary Service | Servicio responsable de gestionar el ciclo de vida de los itinerarios. |
| Adapter | Componente que traduce una interfaz interna a la de una dependencia externa. |
| Puerto | Contrato (interfaz) que define cómo interactúa una capa con una dependencia. |
| Evento de integración | Mensaje que comunica un hecho relevante a otros contextos o servicios. |
| Outbox | Tabla de mensajes pendientes que garantiza la publicación del evento junto con la transacción de base de datos. |

## 4. Contextos delimitados

### 4.1. Contexto de aeropuertos

**Servicio:** Airport Service.

Responsabilidades:

- Consultar la fuente externa.
- Convertir modelos externos a modelos internos.
- Exponer consultas de aeropuertos.
- Encapsular los detalles del proveedor.

No administra itinerarios ni envía notificaciones.

### 4.2. Contexto de itinerarios

**Servicio:** Itinerary Service.

Responsabilidades:

- Gestionar el ciclo de vida de un itinerario.
- Validar los datos requeridos.
- Solicitar la validación de aeropuertos.
- Persistir itinerarios.
- Originar el evento de creación.

Este contexto es propietario de los itinerarios y sus reglas de negocio.

### 4.3. Contexto de notificaciones

**Componentes:** Event Trigger, SendNotificationFunction y su base de datos `notification_db` (Fase 6).

Responsabilidades:

- Interpretar el evento recibido (la función valida el contrato v1 con su propio esquema: no importa código de Itinerary Service).
- Procesar la solicitud de notificación.
- Simular el envío.
- Registrar el historial.

No es propietario de los itinerarios ni debe modificar directamente su base de datos. Referencia el itinerario solo por su `itinerary_id`.

## 5. Entidades y modelos principales

### 5.1. Itinerary

Raíz de agregado del contexto de planificación de itinerarios.

Atributos confirmados (Fase 3, ADR-015 al ADR-018):

| Atributo | Tipo | Descripción |
|---|---|---|
| `id` | UUID | Identificador único generado en la creación. |
| `traveler_name` | str | Nombre del viajero; no puede estar vacío ni solo espacios. |
| `traveler_email` | str \| None | Correo electrónico opcional del viajero. |
| `departure_airport_id` | int | ID del aeropuerto de salida; debe existir en el catálogo. |
| `arrival_airport_id` | int | ID del aeropuerto de llegada; debe existir en el catálogo; distinto del de salida. |
| `travel_date` | datetime (con tz) | Fecha y hora de salida con zona horaria; no puede estar en el pasado al crear. |
| `duration_minutes` | int | Duración estimada en minutos; mayor que cero. |
| `created_at` | datetime | Marca de tiempo de creación en UTC. |
| `updated_at` | datetime | Marca de tiempo de la última modificación en UTC. |

### 5.2. Airport

Modelo interno que representa un aeropuerto.

Sus atributos definitivos dependerán de los campos que realmente entregue API Colombia y de su transformación al modelo interno.

No se asumirá que la fuente externa contiene coordenadas, códigos o identificadores específicos sin comprobarlo.

### 5.3. ItineraryCreatedEvent

Representa el hecho de que un itinerario ha sido creado y puede comunicarse a otros componentes.

El contrato de integración se especificará en la documentación de eventos.

### 5.4. NotificationRecord

Registro de una notificación procesada (Fase 6, ADR-029 y ADR-030). Se guarda en la tabla `notification_history`.

| Atributo | Tipo | Descripción |
|---|---|---|
| `id` | UUID | Identificador de la notificación. |
| `event_id` | UUID | `event_id` del evento recibido. Es **único**: clave de idempotencia. |
| `itinerary_id` | UUID | Itinerario notificado (referencia por id a otro contexto). |
| `recipient` | str \| None | Correo del viajero; `None` si el itinerario no tiene correo. |
| `channel` | str | `simulated-email`. |
| `message` | str | Texto de la notificación; no puede estar vacío. |
| `status` | `SENT` \| `SKIPPED` | `SENT` si se envió; `SKIPPED` si no había destinatario. |
| `status_reason` | str \| None | Motivo cuando el estado es `SKIPPED`. |
| `correlation_id` | str \| None | Correlation ID del evento. |
| `processed_at` | datetime (con tz) | Cuándo se procesó. |

Regla del destinatario (`NotificationRecord.create`): con correo → `SENT`; sin correo (nulo o vacío) → `SKIPPED`, sin destinatario y con el motivo. Un registro `SENT` necesita destinatario; uno `SKIPPED` no lo tiene y debe explicar el motivo.

## 6. Reglas del dominio

Todas las reglas siguientes están confirmadas (ADR-015):

- El nombre del viajero no puede estar vacío ni contener solo espacios.
- El aeropuerto de salida y el de llegada deben ser diferentes.
- La duración debe ser mayor que cero minutos.
- La fecha de viaje debe incluir zona horaria.
- La fecha de viaje no puede estar en el pasado al momento de crear el itinerario (la regla no aplica al actualizar).
- Los aeropuertos de salida y llegada deben existir en el catálogo según Airport Service antes de guardar el itinerario.
- "Aeropuerto no existe" (404 de Airport Service) y "Airport Service no disponible" (503 o 504) se tratan de forma distinta en la capa de aplicación.
- La creación de un itinerario origina el evento `ItineraryCreatedEvent`.
- El historial de notificaciones se mantiene separado de los datos de itinerarios.
- Un evento se notifica una sola vez: si su `event_id` ya está en el historial, no se vuelve a notificar (ADR-030).
- Sin `traveler_email` no se envía la notificación: se registra como `SKIPPED` con el motivo (ADR-030).

## 7. Relación entre DDD y arquitectura hexagonal

DDD ayuda a organizar el modelo del negocio y los límites de sus contextos.

La arquitectura hexagonal permite que las reglas de negocio se mantengan independientes de tecnologías como FastAPI, PostgreSQL, RabbitMQ y la API externa.

El patrón Adapter se utilizará para implementar las traducciones entre los contratos internos y los sistemas externos.

## 8. Evolución del modelo

Las definiciones de este documento se consideran una primera versión del lenguaje ubicuo y del modelo del dominio.

Cualquier cambio importante deberá justificarse y reflejarse en los documentos relacionados.
