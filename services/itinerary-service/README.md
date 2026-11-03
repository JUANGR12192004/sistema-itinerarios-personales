# Itinerary Service

Microservicio de gestión de itinerarios de viaje. Permite crear, consultar, actualizar y eliminar itinerarios entre aeropuertos colombianos. Valida que los aeropuertos existan consultando Airport Service antes de guardar.

## Requisitos previos

- Python 3.12
- Docker Desktop (para PostgreSQL)
- Airport Service corriendo en `http://localhost:8001`

## Configuración inicial (una vez por equipo)

```powershell
# Permitir activar entornos virtuales
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

## Instalación

```powershell
cd services\itinerary-service
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Base de datos PostgreSQL

```powershell
# Levantar el contenedor (solo la primera vez o si no está corriendo)
docker run -d --name itinerary-postgres `
  -e POSTGRES_USER=itinerary `
  -e POSTGRES_PASSWORD=itinerary `
  -e POSTGRES_DB=itinerary_db `
  -p 5433:5432 `
  postgres:16-alpine

# Aplicar la migración
cd services\itinerary-service
.\.venv\Scripts\Activate.ps1
alembic upgrade head
```

## Variables de entorno

Copia `.env.example` a `.env` y ajusta los valores si es necesario:

```powershell
copy .env.example .env
```

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://itinerary:itinerary@localhost:5433/itinerary_db` | Conexión a PostgreSQL |
| `AIRPORT_SERVICE_URL` | `http://localhost:8001` | URL de Airport Service |
| `AIRPORT_SERVICE_TIMEOUT_SECONDS` | `5.0` | Timeout en segundos para llamadas a Airport Service |
| `LOG_LEVEL` | `INFO` | Nivel de logging |

## Ejecución

```powershell
cd services\itinerary-service
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

Swagger UI disponible en: `http://localhost:8002/docs`

## Pruebas

```powershell
cd services\itinerary-service
.\.venv\Scripts\Activate.ps1

# Todas las pruebas (integración se omite si PostgreSQL no está disponible)
pytest -v

# Solo pruebas unitarias y de API (sin PostgreSQL)
pytest -v tests\domain tests\application tests\infrastructure tests\api

# Solo pruebas de integración (requiere PostgreSQL)
pytest -v tests\integration
```

## Endpoints

| Método | Ruta | Descripción | Éxito |
|---|---|---|---|
| `POST` | `/itineraries` | Crear itinerario | 201 |
| `GET` | `/itineraries` | Listar todos | 200 |
| `GET` | `/itineraries/{id}` | Obtener por ID | 200 |
| `PUT` | `/itineraries/{id}` | Actualizar | 200 |
| `DELETE` | `/itineraries/{id}` | Eliminar | 204 |
| `GET` | `/health` | Estado del servicio | 200 |

## Estructura

```
app/
  domain/           → Itinerary (agregado), reglas de negocio, excepciones
  application/      → Puertos (interfaces), casos de uso, excepciones de aplicación
  infrastructure/
    persistence/    → SqlAlchemyItineraryRepository, modelos ORM, session factory
    airport_client/ → HttpAirportCatalogAdapter (llama a Airport Service)
    messaging/      → NoopEventPublisher (Fase 3); reemplazado en Fase 4
  api/              → Rutas, esquemas Pydantic, manejador de errores, dependencias
  main.py           → Creación de la app FastAPI
alembic/            → Migraciones de base de datos
tests/
  domain/           → Pruebas de dominio (sin dependencias externas)
  application/      → Pruebas de FakeItineraryRepository
  infrastructure/   → Pruebas de HttpAirportCatalogAdapter (respx)
  integration/      → Pruebas contra PostgreSQL real (SKIPPED en CI)
  api/              → Pruebas de rutas con fakes inyectados
```
