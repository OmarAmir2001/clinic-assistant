# app/db/database.py
"""How the app reaches the database. The engine is the line to the database; a session is one conversation on it."""
import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.core.errors import UnavailableError

logger = logging.getLogger(__name__)

TRIES = 10  # a database may need a few seconds to start, so try more than once


def make_engine(database_url: str) -> AsyncEngine:
    """One engine per program. The address says which database: SQLite file or PostgreSQL server."""
    return create_async_engine(database_url)


def make_sessions(engine: AsyncEngine) -> async_sessionmaker:
    """A factory for sessions. Each `async with sessions() as session:` is one conversation."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def check_database(engine: AsyncEngine) -> None:
    """Called once at startup: can we reach the database?"""
    for attempt in range(1, TRIES + 1):
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            # SQLAlchemy prints the address with the password hidden as ***
            logger.info("Connected to the database at %s", engine.url)
            return
        except (OSError, SQLAlchemyError) as error:
            reason = type(getattr(error, "orig", None) or error).__name__
            logger.warning("Database not ready (try %d of %d): %s", attempt, TRIES, reason)
            await asyncio.sleep(1)
    raise UnavailableError(f"Can't reach the database at {engine.url}. Is it running?")
