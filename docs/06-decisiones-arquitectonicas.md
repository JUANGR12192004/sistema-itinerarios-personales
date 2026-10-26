
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

## ADR-011 — Idioma del código y de la documentación

**Estado:** Aceptada (Fase 1).

### Contexto

El equipo escribe y sustenta en español, pero las librerías, frameworks y convenciones de programación usan el inglés. Mezclar idiomas dentro del código dificulta su lectura.

### Decisión

- El código (clases, funciones, variables, rutas, códigos de error) se escribe en inglés.
- La documentación, los comentarios y los mensajes de error para el usuario se escriben en español.
- Los términos del código siguen el lenguaje ubicuo definido en `03-dominio.md` (por ejemplo `Itinerary`, `traveler_name`, `departure_airport_id`).

### Justificación

El código queda coherente con el ecosistema (FastAPI, Pydantic, SQLAlchemy) y la documentación sigue siendo accesible para el equipo y para la evaluación del curso.

### Consecuencias

Cada término del negocio debe tener una única traducción en el código, registrada en el lenguaje ubicuo, para evitar sinónimos.

## ADR-012 — Contrato HTTP y formato único de errores

**Estado:** Aceptada (Fase 1) para Airport Service. Los endpoints de Itinerary Service se confirmarán en la Fase 3.

### Contexto

Los clientes (Itinerary Service, Gateway, Frontend) necesitan saber qué endpoints existen y cómo interpretar un error sin importar qué servicio lo generó.

### Decisión

Airport Service expone:

| Método y ruta | Éxito | Errores |
|---|---|---|
| `GET /airports` | 200 | 502, 503 |
| `GET /airports/{id}` | 200 | 404, 422, 502, 503 |
| `GET /airports/map-data` | 200 | 502, 503 |
| `GET /health` | 200 | — |

Todos los servicios responden los errores con el mismo formato:

```json
{
  "error": {
    "code": "AIRPORT_NOT_FOUND",
    "message": "El aeropuerto con id 999 no existe",
    "details": {"field": "arrival_airport_id"}
  },
  "correlation_id": "3f2a..."
}
```

Códigos HTTP: 404 recurso no encontrado, 422 validación, 502 respuesta inesperada del proveedor externo, 503 dependencia no disponible, 504 timeout (Fase 2). Los valores de `code` van en inglés y en MAYÚSCULAS_CON_GUIONES_BAJOS.

### Justificación

Un único formato permite que los clientes manejen los errores de forma uniforme, y distinguir 404, 502 y 503 permite saber si el problema es del dato solicitado, del proveedor o de la disponibilidad.

### Consecuencias

- Cada servicio necesita un manejador centralizado que traduzca las excepciones del dominio y de la aplicación a este formato.
- Cambiar un endpoint o un código de error es un cambio de contrato y debe registrarse.

## ADR-013 — Puertos para las dependencias externas de Itinerary Service

**Estado:** Aceptada (Fase 1). Corrige el diagrama de componentes de `05-diagramas.md`.

### Contexto

La primera versión del diagrama de componentes mostraba los casos de uso de Itinerary Service llamando directamente a la capa de aplicación de Airport Service y publicando directamente en RabbitMQ. Eso contradice la arquitectura hexagonal (ADR-002): un servicio no accede a las capas internas de otro, y los casos de uso no dependen de infraestructura concreta.

### Decisión

- La validación de aeropuertos se hace mediante el puerto `AirportCatalog`, implementado por `HttpAirportCatalogAdapter`, que llama al endpoint REST `GET /airports/{id}` de Airport Service.
- La publicación de eventos se hace mediante el puerto `EventPublisher`. En la Fase 4 lo implementa un publicador de RabbitMQ y en la Fase 5 un adaptador Outbox, sin cambiar el caso de uso.

### Justificación

Los casos de uso quedan independientes del protocolo HTTP y del broker de mensajería, y se pueden probar con implementaciones falsas de los puertos.

### Consecuencias

- Itinerary Service solo conoce el contrato REST publicado por Airport Service (ADR-012).
- El paso de publicación directa (Fase 4) a Outbox (Fase 5) se limita a cambiar el adaptador inyectado.

## 2. Revisión de decisiones

Las decisiones pendientes deberán resolverse antes de implementar los componentes afectados.

Toda modificación de una decisión aceptada deberá incluir la razón del cambio y sus consecuencias.
