
# 04. Comunicación y eventos

## 1. Objetivo

Definir cómo se comunicarán los componentes del Sistema de Itinerarios Personales.

Se utilizarán dos mecanismos principales:

- HTTP/REST para operaciones síncronas.
- RabbitMQ para mensajería asíncrona basada en eventos.

## 2. Comunicación HTTP

### 2.1. Consulta de aeropuertos

El consumidor realizará una solicitud a Airport Service.

Airport Service consultará su puerto de salida, implementado mediante el Adapter correspondiente, para obtener información de API Colombia.

La respuesta se transformará al modelo interno antes de entregarse al consumidor.

### 2.2. Validación de itinerarios

Antes de guardar un itinerario, Itinerary Service consultará Airport Service para verificar los aeropuertos de salida y llegada.

Si alguno no existe, el itinerario no deberá persistirse como válido.

Si Airport Service no está disponible, Itinerary Service deberá gestionar el fallo sin confundirlo con una respuesta que indique que el aeropuerto no existe.

## 3. Comunicación basada en eventos

### 3.1. Evento de integración

El evento inicial será:

`ItineraryCreatedEvent`

Su propósito es comunicar a otros componentes que se ha creado un itinerario.

El consumidor inicial será el sistema de notificaciones.

### 3.2. Contrato conceptual del evento

El contrato definitivo se fijará antes de implementar RabbitMQ.

Como mínimo, deberá contemplar:

- Identificador único del evento.
- Tipo de evento.
- Versión del contrato.
- Fecha y hora de ocurrencia.
- Identificador del itinerario.
- Datos mínimos necesarios para procesar la notificación.

Los nombres definitivos, tipos de datos y formato de serialización se establecerán en el contrato versionado.

### 3.3. RabbitMQ

La configuración utilizará los siguientes conceptos:

- **Exchange:** recibe los mensajes publicados.
- **Routing Key:** determina cómo se enruta un mensaje.
- **Queue:** almacena los mensajes pendientes de consumo.
- **Consumer:** recibe y procesa mensajes.
- **Acknowledgement:** confirma el procesamiento según la política definida.

Los nombres concretos del exchange, la cola y la routing key se decidirán al implementar esta fase.

### 3.4. Tratamiento de errores

El consumidor deberá evitar confirmar un mensaje como procesado antes de completar las operaciones que su política de procesamiento considere necesarias.

Se definirán estrategias de reintento, tratamiento de mensajes fallidos y prevención de duplicados.

La entrega de mensajes puede repetirse; por tanto, el procesamiento deberá diseñarse considerando la idempotencia.

## 4. Evento de dominio y evento de integración

### Evento de dominio

Representa un hecho relevante dentro de un contexto de negocio.

Puede utilizarse dentro del modelo de dominio para comunicar que ocurrió algo significativo.

### Evento de integración

Representa un hecho que un contexto comunica a otros sistemas o servicios mediante un contrato compartido.

`ItineraryCreatedEvent` se tratará como evento de integración para notificar la creación de un itinerario al sistema de notificaciones.

Un evento de dominio y uno de integración pueden estar relacionados, pero no son necesariamente el mismo objeto ni tienen que compartir exactamente el mismo formato.

## 5. Diferencias entre HTTP y eventos

| Característica | HTTP/REST | Evento |
|---|---|---|
| Interacción | Solicitud y respuesta | Publicación y consumo |
| Acoplamiento temporal | El consumidor espera una respuesta | El productor no necesita esperar al consumidor final |
| Uso principal | Consultar o validar aeropuertos | Comunicar la creación de itinerarios |
| Fallos | Deben gestionarse en la solicitud | Deben gestionarse durante publicación y consumo |
| Tecnología | FastAPI y HTTP | RabbitMQ |

## 6. Transactional Outbox

Itinerary Service deberá incorporar posteriormente el patrón Transactional Outbox para reducir el riesgo de que se guarde un itinerario sin que quede registrado el evento que debe publicarse.

La idea consiste en guardar, dentro de una misma transacción de base de datos, el itinerario y un registro del evento pendiente.

Un proceso independiente publicará posteriormente los eventos pendientes en RabbitMQ.

La publicación y el consumo requerirán manejo de duplicados y recuperación ante fallos.

## 7. Integración serverless

El evento publicado en RabbitMQ deberá llegar al componente responsable de ejecutar SendNotificationFunction.

El mecanismo de integración dependerá de la plataforma serverless elegida.

No se asumirá que RabbitMQ puede activar directamente cualquier función sin un adaptador, consumidor o integración compatible.

## 8. AsyncAPI

Se creará una especificación AsyncAPI para documentar:

- Canales de comunicación.
- Mensajes.
- Contratos de eventos.
- Productores y consumidores.
- Protocolos y mecanismos de transporte.

La especificación deberá corresponder al contrato implementado, no solamente a una descripción conceptual.

## 9. Evolución del contrato

Los cambios incompatibles en un evento deberán gestionarse mediante una estrategia explícita de versionado y compatibilidad.
