# app/api/routes/health.py
from fastapi import APIRouter

from app.api.dependencies import SettingsDep
from app.api.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: SettingsDep) -> HealthResponse:
    """Is the service running? Used by people, scripts and (later) the hosting platform."""
    return HealthResponse(status="ok", app=settings.APP_NAME, version=settings.APP_VERSION)
