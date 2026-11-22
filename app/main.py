# app/main.py
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import ValidationError

from app.api.errors import add_error_handlers
from app.api.routes import appointments, chat, doctors, health
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.providers.llm.openai_compatible import OpenAICompatibleLLM
from app.repositories.appointments import InMemoryAppointmentRepository
from app.repositories.doctors import DoctorRepository
from app.services.answer import AnswerService
from app.services.booking import BookingService

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts (before `yield`) and once when it stops (after)."""
    settings = app.state.settings
    llm = OpenAICompatibleLLM(settings)
    app.state.answer_service = AnswerService(llm, settings)
    app.state.booking_service = BookingService(
        DoctorRepository(settings.DOCTORS_PATH),
        InMemoryAppointmentRepository(),
    )
    logger.info("%s is ready", settings.APP_NAME)
    yield
    logger.info("%s is shutting down", settings.APP_NAME)


def create_app() -> FastAPI:
    # 1. Settings first: if anything is missing, stop here with a clear message
    try:
        settings = get_settings()
    except ValidationError as error:
        # Show only the setting's name and the problem, never the values (they may be secrets)
        problems = [f"  {problem['loc'][0]}: {problem['msg']}" for problem in error.errors()]
        sys.exit("Configuration error. Check your .env file:\n" + "\n".join(problems))

    # 2. Logging, then the app itself
    setup_logging(settings.LOG_LEVEL)
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Answers clinic questions and books appointments at Nile Family Clinic.",
        lifespan=lifespan,
    )
    app.state.settings = settings

    # 3. One error shape for everything, then one router per feature
    add_error_handlers(app)
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(doctors.router)
    app.include_router(appointments.router)
    return app


app = create_app()
