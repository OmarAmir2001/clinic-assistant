# app/core/config.py
from functools import lru_cache
from pathlib import Path

from pydantic import Field, FilePath, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.enums import LogLevel

# The project folder (the one that holds .env), found from this file's place
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Every setting the app needs, read from .env and checked when the app starts."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore",
        validate_default=True,
    )

    APP_NAME: str = "Clinic Booking Assistant"
    APP_VERSION: str = "0.3.0"
    LOG_LEVEL: LogLevel = LogLevel.INFO

    # The LLM: no defaults, so the app refuses to start without them
    LLM_BASE_URL: str
    LLM_API_KEY: SecretStr
    LLM_MODEL: str
    LLM_TIMEOUT_SECONDS: float = Field(default=30, gt=0)

    # The clinic's data files: they must exist
    CLINIC_INFO_PATH: FilePath = BASE_DIR / "data" / "clinic_info.md"
    DOCTORS_PATH: FilePath = BASE_DIR / "data" / "doctors.json"

    # Warn in the log when one question sends more tokens than this
    PROMPT_TOKENS_WARNING: int = Field(default=3000, gt=0)


@lru_cache
def get_settings() -> Settings:
    """Read the settings once; everyone shares the same object."""
    return Settings()
