"""Punto de entrada de Itinerary Service."""

import logging

from fastapi import FastAPI

from app.api.error_handler import add_error_handlers
from app.api.routes import router
from app.config import get_settings

settings = get_settings()

logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Itinerary Service",
    description="Gestión de itinerarios de viaje entre aeropuertos colombianos.",
    version="1.0.0",
)

add_error_handlers(app)
app.include_router(router)


@app.get("/health", tags=["Salud"])
def health() -> dict:
    return {"status": "ok", "service": settings.service_name}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8002, reload=True)
