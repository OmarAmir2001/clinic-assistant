# app/db/connection.py
import asyncio
import logging

import asyncpg

from app.core.config import Settings
from app.core.errors import UnavailableError

logger = logging.getLogger(__name__)

# The errors that mean "the database didn't answer": not running, wrong address,
# still starting up, wrong password, or too slow
CONNECTION_ERRORS = (OSError, TimeoutError, asyncpg.PostgresError)


class Database:
    """How the app reaches PostgreSQL. Session 6 adds a connection pool and SQLAlchemy here."""

    def __init__(self, settings: Settings):
        self.url = settings.database_url
        self.place = settings.database_place
        self.attempts = settings.DB_CONNECT_ATTEMPTS
        self.delay = settings.DB_CONNECT_DELAY_SECONDS

    async def ping(self) -> None:
        """Open a connection, ask the smallest possible question, close it."""
        try:
            connection = await asyncpg.connect(self.url, timeout=3)
            try:
                await connection.fetchval("SELECT 1")
            finally:
                await connection.close()
        except CONNECTION_ERRORS as error:
            raise UnavailableError(f"The database at {self.place} is not answering.") from error

    async def wait_until_ready(self) -> None:
        """Called once at startup. The database may still be starting, so try a few times."""
        for attempt in range(1, self.attempts + 1):
            try:
                await self.ping()
                logger.info("Database %s is ready", self.place)
                return
            except UnavailableError as error:
                # The cause's type name is enough to debug (ConnectionRefusedError,
                # InvalidPasswordError ...) and never contains the password
                reason = type(error.__cause__).__name__
                logger.warning("Database not ready (try %d of %d): %s", attempt, self.attempts, reason)
                if attempt < self.attempts:
                    await asyncio.sleep(self.delay)
        raise UnavailableError(
            f"Gave up waiting for the database at {self.place}. "
            "Is it running (docker compose up -d db), and are the POSTGRES_ settings in .env right?"
        )
