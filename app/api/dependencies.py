# app/api/dependencies.py
from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.services.answer import AnswerService
from app.services.booking import BookingService
from app.services.ingestion import IngestionService


def get_answer_service(request: Request) -> AnswerService:
    return request.app.state.answer_service


def get_booking_service(request: Request) -> BookingService:
    return request.app.state.booking_service


def get_ingestion_service(request: Request) -> IngestionService:
    return request.app.state.ingestion_service


# Short names for "give me this object" in a route's parameters
SettingsDep = Annotated[Settings, Depends(get_settings)]
AnswerServiceDep = Annotated[AnswerService, Depends(get_answer_service)]
BookingServiceDep = Annotated[BookingService, Depends(get_booking_service)]
IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]
