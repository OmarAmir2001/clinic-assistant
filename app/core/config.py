# app/core/config.py
from functools import lru_cache
from pathlib import Path

from pydantic import Field, FilePath, SecretStr, model_validator
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
    APP_VERSION: str = "0.6.0"
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

    # Uploaded documents: where they go, and how big they may be
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"
    MAX_UPLOAD_MB: int = Field(default=5, gt=0, le=50)
    MAX_PDF_PAGES: int = Field(default=50, gt=0)

    # Chunking: the size of each piece, and how much of the previous piece it repeats
    CHUNK_SIZE: int = Field(default=800, ge=200, le=4000)
    CHUNK_OVERLAP: int = Field(default=120, ge=0)

    # The database (Session 5). By default a SQLite file in data/; for PostgreSQL, set DATABASE_URL in .env
    DATABASE_URL: str = f"sqlite+aiosqlite:///{(BASE_DIR / 'data' / 'clinic.db').as_posix()}"

    @model_validator(mode="after")
    def check_overlap(self) -> "Settings":
        # An overlap as big as the chunk would repeat forever; half is already a lot
        if self.CHUNK_OVERLAP >= self.CHUNK_SIZE // 2:
            raise ValueError("CHUNK_OVERLAP must be less than half of CHUNK_SIZE")
        return self

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Read the settings once; everyone shares the same object."""
    return Settings()
