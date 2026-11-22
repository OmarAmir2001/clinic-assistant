# app/api/routes/health.py
from fastapi import APIRouter

from app.api.dependencies import DatabaseDep, SettingsDep
from app.api.schemas.health import HealthResponse, ReadyResponse

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: SettingsDep) -> HealthResponse:
    """Is the service running? Used by people, scripts and (later) the hosting platform."""
    return HealthResponse(status="ok", app=settings.APP_NAME, version=settings.APP_VERSION)


@router.get("/health/ready")
async def ready(database: DatabaseDep) -> ReadyResponse:
    """Can the service do its work right now? It needs the database, so ask it.
    If the database doesn't answer, the error handler turns that into a 503."""
    await database.ping()
    return ReadyResponse(status="ok", database="ok")
