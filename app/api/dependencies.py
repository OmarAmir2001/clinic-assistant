# app/api/dependencies.py
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.repositories.appointments import AppointmentRepository
from app.repositories.chunks import ChunkRepository
from app.repositories.doctors import DoctorRepository
from app.repositories.documents import DocumentRepository
from app.repositories.slots import SlotRepository
from app.services.answer import AnswerService
from app.services.booking import BookingService
from app.services.ingestion import IngestionService
from app.services.search import SearchService


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One database session per request, closed when the request ends (whatever happened)."""
    async with request.app.state.sessions() as session:
        yield session


SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_answer_service(request: Request) -> AnswerService:
    return request.app.state.answer_service


def get_booking_service(session: SessionDep) -> BookingService:
    # Built for each request, around that request's session
    return BookingService(session, DoctorRepository(session), SlotRepository(session), AppointmentRepository(session))


def get_ingestion_service(request: Request, session: SessionDep, settings: SettingsDep) -> IngestionService:
    state = request.app.state
    return IngestionService(state.files, DocumentRepository(session), state.embeddings, session, settings)


def get_search_service(request: Request, session: SessionDep, settings: SettingsDep) -> SearchService:
    # The two models are loaded once at startup and shared; the repository is per request
    state = request.app.state
    return SearchService(ChunkRepository(session), state.embeddings, state.reranker, settings)


# Short names for "give me this object" in a route's parameters
AnswerServiceDep = Annotated[AnswerService, Depends(get_answer_service)]
BookingServiceDep = Annotated[BookingService, Depends(get_booking_service)]
IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]
SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]
