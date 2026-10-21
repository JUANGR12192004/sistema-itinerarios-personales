
# 01. Planificación del proyecto

## 1. Información general

- **Nombre:** Sistema de Itinerarios Personales.
- **Asignatura:** Arquitecturas de Software Emergentes.
- **Tipo:** Proyecto académico de software distribuido.
- **Estado:** Planificación y arquitectura.
- **Repositorio:** sistema-itinerarios-personales.

## 2. Problema y propósito

El proyecto busca desarrollar un sistema para planificar viajes que permita consultar aeropuertos colombianos, administrar itinerarios y generar notificaciones asíncronas.

El sistema servirá como ejercicio práctico para estudiar la separación de responsabilidades, la comunicación entre servicios, la integración con sistemas externos, la resiliencia y la observabilidad.

## 3. Objetivo general

Diseñar e implementar un sistema distribuido de planificación de viajes que integre microservicios, arquitectura basada en eventos y serverless.

## 4. Objetivos específicos

1. Consultar información de aeropuertos mediante API Colombia.
2. Implementar un adaptador que desacople el dominio de la API externa.
3. Exponer endpoints REST para consultar aeropuertos.
4. Construir un servicio independiente para gestionar itinerarios.
5. Validar los aeropuertos antes de guardar un itinerario.
6. Persistir los itinerarios en PostgreSQL.
7. Publicar un evento de integración cuando se cree un itinerario.
8. Procesar el evento mediante RabbitMQ y un componente de notificaciones.
9. Implementar una función serverless para simular el envío de notificaciones.
10. Aplicar mecanismos de resiliencia, caché y observabilidad.
11. Construir una interfaz web con mapa interactivo.
12. Documentar, probar y contenerizar progresivamente el sistema.

## 5. Alcance funcional

### 5.1. Aeropuertos

- Consultar aeropuertos colombianos desde API Colombia.
- Consultar un aeropuerto por identificador.
- Convertir la respuesta externa a un modelo interno.
- Exponer la información mediante endpoints REST.
- Preparar los datos necesarios para su representación en Plotly JS.
- Incorporar caché y resiliencia en la fase correspondiente.

### 5.2. Itinerarios

Cada itinerario incluirá, como mínimo:

- Nombre del usuario.
- Identificador del aeropuerto de salida.
- Identificador del aeropuerto de llegada.
- Fecha del viaje.
- Duración en minutos.

El servicio permitirá crear, consultar, actualizar y eliminar itinerarios.

Antes de persistir un itinerario, consultará Airport Service para validar los aeropuertos.

### 5.3. Notificaciones

- Publicar un evento de integración cuando se cree un itinerario.
- Transportar el evento mediante RabbitMQ.
- Procesarlo mediante el sistema de notificaciones.
- Ejecutar SendNotificationFunction.
- Simular el envío y registrar el historial.
- Manejar errores de procesamiento.

### 5.4. Interfaz web

- Consultar aeropuertos.
- Mostrar aeropuertos en un mapa con Plotly JS.
- Crear itinerarios.
- Consultar itinerarios.
- Actualizar itinerarios.
- Eliminar itinerarios.

El frontend no consumirá directamente API Colombia.

## 6. Requisitos no funcionales

Los siguientes requisitos representan objetivos de diseño que deberán verificarse mediante pruebas:

- **Modularidad:** separar dominio, aplicación e infraestructura.
- **Desacoplamiento:** evitar dependencias directas del dominio respecto de la API externa.
- **Resiliencia:** controlar fallos y tiempos de espera de servicios externos.
- **Persistencia:** mantener los datos de cada microservicio bajo su propia responsabilidad.
- **Mantenibilidad:** organizar el código de forma comprensible y extensible.
- **Observabilidad:** incorporar logs, métricas y trazas.
- **Documentación:** documentar endpoints y eventos.
- **Pruebas:** verificar reglas de negocio, integración y comunicación.
- **Contenerización:** facilitar la ejecución mediante Docker.
- **Manejo de errores:** devolver respuestas HTTP apropiadas y registrar fallos.

Los objetivos cuantitativos de rendimiento, disponibilidad y latencia se definirán cuando exista información suficiente para establecer valores medibles.

## 7. Restricciones de diseño

- No mezclar reglas de negocio con controladores.
- No mezclar reglas de negocio con detalles de infraestructura.
- No consumir API Colombia directamente desde el frontend.
- No compartir una única base de datos entre los microservicios de negocio.
- No utilizar HTTP como sustituto de los eventos cuando se requiera comunicación asíncrona.
- No incorporar complejidad antes de que la funcionalidad básica esté probada.
- No avanzar a la siguiente fase sin validar la fase actual.

## 8. Fases de implementación

| Fase | Entregable |
|---|---|
| 0 | Planificación, arquitectura y documentación inicial |
| 1 | Airport Service funcional con Adapter y pruebas básicas |
| 2 | Redis, timeout, retry, backoff, circuit breaker y fallback |
| 3 | Itinerary Service, PostgreSQL, CRUD y Alembic |
| 4 | RabbitMQ, evento de integración y contrato AsyncAPI |
| 5 | Patrón Transactional Outbox |
| 6 | SendNotificationFunction y registro de notificaciones |
| 7 | API Gateway / BFF |
| 8 | Frontend y mapa interactivo |
| 9 | Logs estructurados, trazas, métricas y dashboards |
| 10 | Orquestación con Docker Compose |
| 11 | Pruebas unitarias, integración, API y flujo completo |
| 12 | Documentación final y entrega académica |

## 9. Criterios de finalización de la Fase 0

La planificación se considerará lista para aprobación cuando existan:

- Arquitectura general definida.
- Responsabilidades de los servicios documentadas.
- Contextos delimitados y lenguaje ubicuo inicial.
- Entidades y conceptos principales identificados.
- Comunicación síncrona y asíncrona especificada.
- Bases de datos y propiedad de los datos definidas.
- Flujo de creación de itinerarios documentado.
- Diagramas de arquitectura, componentes y secuencia.
- Decisiones técnicas registradas, incluidas las pendientes.
- Estructura documental preparada en el repositorio.

La aprobación de esta fase no significa que la implementación esté terminada.

## 10. Gestión del desarrollo

Cada fase tendrá instrucciones, entregables y pruebas propias. Las modificaciones a decisiones o documentos anteriores deberán justificarse antes de realizarse.

El avance entre fases requerirá confirmación explícita.
