# app/db/connection.py
import asyncio
import logging

import asyncpg

from app.core.config import Settings
from app.core.errors import UnavailableError

logger = logging.getLogger(__name__)

TRIES = 10  # the database may need a few seconds to start, so try more than once


async def check_database(settings: Settings) -> None:
    """Called once when the app starts: can we reach PostgreSQL?"""
    where = f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}"  # never log the password
    for attempt in range(1, TRIES + 1):
        try:
            connection = await asyncpg.connect(settings.database_url, timeout=3)
            await connection.close()
            logger.info("Connected to the database at %s", where)
            return
        except (OSError, asyncpg.PostgresError) as error:
            logger.warning("Database not ready (try %d of %d): %s", attempt, TRIES, type(error).__name__)
            await asyncio.sleep(1)
    raise UnavailableError(f"Can't reach the database at {where}. Is it running? Try: docker compose up -d db")
