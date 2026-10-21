
# 06. Registro de decisiones arquitectónicas

## 1. Propósito

Registrar las decisiones arquitectónicas relevantes del Sistema de Itinerarios Personales, incluyendo su contexto, justificación, consecuencias y estado.

Las decisiones pendientes no deben considerarse definitivas hasta ser evaluadas.

## ADR-001 — Uso de microservicios

**Estado:** Aceptada para el diseño.

### Contexto

El proyecto requiere separar la consulta de aeropuertos, la gestión de itinerarios y el procesamiento de notificaciones.

### Decisión

Organizar el sistema mediante Airport Service, Itinerary Service y los componentes del sistema de notificaciones.

### Justificación

Cada componente tendrá una responsabilidad delimitada y contratos explícitos de comunicación.

### Consecuencias

- Se deben gestionar llamadas entre servicios.
- Se requiere tratamiento de errores de comunicación.
- El despliegue y las pruebas de integración serán más complejos que en una aplicación monolítica.
- Se evita concentrar toda la lógica en un único componente.

## ADR-002 — Arquitectura hexagonal

**Estado:** Aceptada para el diseño.

### Contexto

Los servicios necesitan interactuar con tecnologías externas sin acoplar sus reglas de negocio a ellas.

### Decisión

Separar dominio, casos de uso, puertos y adaptadores donde corresponda.

### Justificación

Permite sustituir dependencias externas y probar la lógica de negocio con mayor independencia de la infraestructura.

### Consecuencias

Se requiere una estructura de código más explícita, pero se facilita el mantenimiento y las pruebas.

## ADR-003 — Patrón Adapter para API Colombia

**Estado:** Aceptada para el diseño.

### Contexto

Airport Service depende de una API externa cuyo contrato puede cambiar.

### Decisión

Definir un puerto interno para consultar aeropuertos e implementar un Adapter para API Colombia.

### Justificación

La lógica interna no dependerá directamente del formato de respuesta del proveedor.

### Consecuencias

- Se necesita transformar modelos externos a modelos internos.
- Se pueden sustituir proveedores sin modificar directamente los casos de uso.
- Las pruebas del adaptador deberán verificar la traducción de datos y los errores de integración.

## ADR-004 — PostgreSQL independiente para itinerarios

**Estado:** Aceptada para el diseño.

### Contexto

Itinerary Service debe persistir y administrar itinerarios.

### Decisión

Utilizar PostgreSQL como base de datos de itinerarios y mantener la propiedad de los datos dentro de Itinerary Service.

### Justificación

El servicio controlará su esquema, sus migraciones y las operaciones sobre sus entidades.

### Consecuencias

Se deberán definir migraciones versionadas y una estrategia de respaldo y configuración.

La tecnología de persistencia del historial de notificaciones se decidirá por separado.

## ADR-005 — RabbitMQ para mensajería

**Estado:** Aceptada para el diseño.

### Contexto

El sistema debe comunicar la creación de itinerarios sin depender de que el procesamiento de notificaciones finalice en la misma solicitud HTTP.

### Decisión

Utilizar RabbitMQ para transportar eventos de integración.

### Justificación

Permite desacoplar temporalmente al productor y al consumidor.

### Consecuencias

Se deberán configurar exchanges, colas, routing keys, confirmaciones, recuperación ante errores e idempotencia.

## ADR-006 — Transactional Outbox

**Estado:** Aceptada como objetivo de implementación.

### Contexto

Guardar un itinerario y publicar un evento son operaciones que involucran dos sistemas diferentes.

### Decisión

Registrar el itinerario y el evento pendiente en una misma transacción de PostgreSQL y publicar el evento mediante un proceso independiente.

### Justificación

Reduce el riesgo de perder la publicación cuando el guardado del itinerario ya se confirmó.

### Consecuencias

Se requiere un worker o publisher, seguimiento de eventos pendientes y manejo de duplicados.

## ADR-007 — Redis para caché

**Estado:** Aceptada para la fase de resiliencia.

### Contexto

Las consultas repetidas pueden aumentar la latencia y la carga sobre API Colombia.

### Decisión

Incorporar Redis en Airport Service para almacenar temporalmente resultados adecuados para caché.

### Justificación

Puede reducir llamadas externas y mejorar el tiempo de respuesta.

### Consecuencias

Se deberán definir expiración, invalidación y comportamiento ante resultados obsoletos o fallos de caché.

## ADR-008 — Tecnología serverless local

**Estado:** Pendiente de decisión.

### Contexto

El proyecto debe ejecutar SendNotificationFunction en un entorno de desarrollo local.

### Alternativas

- LocalStack con AWS Lambda.
- Knative.
- OpenFaaS.

### Criterios de selección

- Facilidad de instalación.
- Compatibilidad con el equipo de desarrollo.
- Integración con el flujo de eventos.
- Complejidad de configuración.
- Facilidad para demostrar el modelo FaaS en la sustentación.

### Decisión final

Se registrará después de comparar las alternativas y comprobar su compatibilidad con el entorno.

## ADR-009 — API Gateway / BFF

**Estado:** Pendiente de selección de tecnología.

### Contexto

El frontend necesita un punto de entrada para acceder a los servicios internos.

### Decisión prevista

Utilizar un gateway que enrute solicitudes sin incorporar lógica de negocio.

### Criterios

- Facilidad de ejecución local.
- Compatibilidad con Docker.
- Enrutamiento hacia FastAPI.
- Posibilidad de incorporar rate limiting.
- Preparación para propagación de JWT.

## ADR-010 — Observabilidad

**Estado:** Aceptada para el diseño.

### Contexto

La distribución del sistema dificulta seguir una operación de extremo a extremo.

### Decisión

Incorporar OpenTelemetry, Jaeger, Prometheus y Grafana, junto con logs estructurados.

### Justificación

Estas herramientas permitirán investigar fallos y analizar trazas, métricas y comportamiento del sistema.

### Consecuencias

Se deberá configurar la instrumentación de los componentes y la propagación de identificadores de correlación.

## 2. Revisión de decisiones

Las decisiones pendientes deberán resolverse antes de implementar los componentes afectados.

Toda modificación de una decisión aceptada deberá incluir la razón del cambio y sus consecuencias.
