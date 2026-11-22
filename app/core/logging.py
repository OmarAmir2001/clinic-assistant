import logging

from app.core.enums import LogLevel


def setup_logging(level: LogLevel) -> None:
    """Send every log line to one place, in one format."""
    # Libraries (openai, httpx, ...) only report warnings and errors
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    # Our own code ("app" and everything under it) reports at the level we chose
    logging.getLogger("app").setLevel(level)
