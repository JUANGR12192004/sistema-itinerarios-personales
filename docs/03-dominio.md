
# 03. Dominio, DDD y contextos delimitados

## 1. Propósito

Definir los conceptos principales del negocio, sus responsabilidades y los límites iniciales de cada contexto.

Esta definición es preliminar y deberá validarse durante la implementación.

## 2. Dominio principal

El dominio principal es la planificación y gestión de itinerarios de viaje.

El sistema necesita identificar aeropuertos válidos, asociarlos a un itinerario y generar una notificación cuando se cree dicho itinerario.

## 3. Lenguaje ubicuo

Se utilizarán los siguientes términos de manera consistente:

| Término | Definición |
|---|---|
| Aeropuerto | Instalación de transporte aéreo identificada por un identificador y sus atributos disponibles. |
| Airport Service | Servicio responsable de consultar y normalizar información de aeropuertos. |
| Itinerario | Registro que representa un viaje planificado. |
| Aeropuerto de salida | Aeropuerto desde el cual comienza el viaje. |
| Aeropuerto de llegada | Aeropuerto al cual se dirige el viaje. |
| Itinerary Service | Servicio responsable de gestionar itinerarios. |
| Evento de integración | Mensaje que comunica un hecho relevante a otros componentes. |
| ItineraryCreatedEvent | Evento que informa que se ha creado un itinerario. |
| Notificación | Resultado de una acción de comunicación simulada asociada a un evento. |
| Adapter | Componente que traduce una interfaz interna a una dependencia externa. |
| Puerto | Contrato que define cómo interactúa una capa con una dependencia. |
| Outbox | Registro persistente de eventos pendientes de publicar. |

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

**Componentes:** sistema de notificaciones y SendNotificationFunction.

Responsabilidades:

- Interpretar el evento recibido.
- Procesar la solicitud de notificación.
- Simular el envío.
- Registrar el historial.

No es propietario de los itinerarios ni debe modificar directamente su base de datos.

## 5. Entidades y modelos principales

### 5.1. Itinerary

Representa un itinerario de viaje.

Atributos mínimos establecidos por los requisitos:

- Identificador del itinerario.
- Nombre del usuario.
- Identificador del aeropuerto de salida.
- Identificador del aeropuerto de llegada.
- Fecha del viaje.
- Duración en minutos.

El tipo exacto del identificador, las restricciones de fechas y las reglas de validación se concretarán antes de implementar el dominio.

### 5.2. Airport

Modelo interno que representa un aeropuerto.

Sus atributos definitivos dependerán de los campos que realmente entregue API Colombia y de su transformación al modelo interno.

No se asumirá que la fuente externa contiene coordenadas, códigos o identificadores específicos sin comprobarlo.

### 5.3. ItineraryCreatedEvent

Representa el hecho de que un itinerario ha sido creado y puede comunicarse a otros componentes.

El contrato de integración se especificará en la documentación de eventos.

### 5.4. NotificationRecord

Concepto que representa el historial de una notificación procesada.

Sus campos definitivos se establecerán al diseñar el procesamiento, la persistencia y el manejo de errores.

## 6. Reglas iniciales del dominio

- Un itinerario debe incluir los datos obligatorios definidos en los requisitos.
- Los aeropuertos de salida y llegada deben existir según Airport Service antes de guardar el itinerario.
- La duración debe expresarse en minutos.
- La creación de un itinerario debe originar el evento correspondiente.
- Los fallos al consultar aeropuertos deben tratarse explícitamente.
- El historial de notificaciones debe mantenerse separado de los datos de itinerarios.

Las reglas adicionales, como la prohibición de que salida y llegada sean el mismo aeropuerto o las restricciones sobre fechas pasadas, quedan pendientes de decisión.

## 7. Relación entre DDD y arquitectura hexagonal

DDD ayuda a organizar el modelo del negocio y los límites de sus contextos.

La arquitectura hexagonal permite que las reglas de negocio se mantengan independientes de tecnologías como FastAPI, PostgreSQL, RabbitMQ y la API externa.

El patrón Adapter se utilizará para implementar las traducciones entre los contratos internos y los sistemas externos.

## 8. Evolución del modelo

Las definiciones de este documento se consideran una primera versión del lenguaje ubicuo y del modelo del dominio.

Cualquier cambio importante deberá justificarse y reflejarse en los documentos relacionados.
