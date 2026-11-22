# app/api/schemas/health.py
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str


class ReadyResponse(BaseModel):
    status: str
    database: str
