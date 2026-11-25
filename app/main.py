# app/main.py
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import ValidationError

from app.api.errors import add_error_handlers
from app.api.limits import BodySizeLimit
from app.api.routes import appointments, chat, doctors, documents, health, search
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.database import check_database, make_engine, make_sessions
from app.db.models import EMBEDDING_DIM
from app.providers.embeddings.e5 import E5Embeddings
from app.providers.llm.openai_compatible import OpenAICompatibleLLM
from app.providers.rerankers.cross_encoder import CrossEncoderReranker
from app.repositories.files import FileStore
from app.services.answer import AnswerService

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts (before `yield`) and once when it stops (after)."""
    settings = app.state.settings

    # The database first: if it's not there, stop now with a clear message
    app.state.engine = make_engine(settings.DATABASE_URL)
    await check_database(app.state.engine)

    # A session factory: each request gets its own session (app/api/dependencies.py)
    app.state.sessions = make_sessions(app.state.engine)
    app.state.files = FileStore(settings.UPLOAD_DIR, settings.max_upload_bytes)

    # The two search models (Session 7): loaded once, shared by every request.
    # The first start downloads them (about 600 MB); after that they load from the cache in seconds.
    app.state.embeddings = E5Embeddings(settings.EMBEDDING_MODEL, settings.EMBEDDING_BATCH_SIZE)
    if app.state.embeddings.dimension != EMBEDDING_DIM:
        raise RuntimeError(
            f"{settings.EMBEDDING_MODEL} makes {app.state.embeddings.dimension}-number vectors, "
            f"but the chunks table stores {EMBEDDING_DIM}. "
            "Change EMBEDDING_DIM in app/db/models.py and reset the database."
        )
    app.state.reranker = CrossEncoderReranker(settings.RERANKER_MODEL)

    llm = OpenAICompatibleLLM(settings)
    app.state.answer_service = AnswerService(llm, settings)
    logger.info("%s is ready", settings.APP_NAME)
    yield
    logger.info("%s is shutting down", settings.APP_NAME)
    await app.state.engine.dispose()


def create_app() -> FastAPI:
    # 1. Settings first: if anything is missing, stop here with a clear message
    try:
        settings = get_settings()
    except ValidationError as error:
        # Show only the setting's name and the problem, never the values (they may be secrets)
        problems = []
        for problem in error.errors():
            # A rule about two settings together (like CHUNK_OVERLAP) has no single field name
            name = problem["loc"][0] if problem["loc"] else "settings"
            problems.append(f"  {name}: {problem['msg']}")
        sys.exit("Configuration error. Check your .env file:\n" + "\n".join(problems))

    # 2. Logging, then the app itself
    setup_logging(settings.LOG_LEVEL)
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Answers clinic questions, books appointments and takes in clinic documents at Nile Family Clinic.",
        lifespan=lifespan,
    )
    app.state.settings = settings

    # 3. No request bigger than the upload limit (plus a little room for the form around the file)
    app.add_middleware(BodySizeLimit, max_bytes=settings.max_upload_bytes + 64 * 1024)

    # 4. One error shape for everything, then one router per feature
    add_error_handlers(app)
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(doctors.router)
    app.include_router(appointments.router)
    app.include_router(documents.router)
    app.include_router(search.router)
    return app


app = create_app()
