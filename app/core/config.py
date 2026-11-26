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
    APP_VERSION: str = "0.10.0"
    LOG_LEVEL: LogLevel = LogLevel.INFO

    # The LLM: no defaults, so the app refuses to start without them
    LLM_BASE_URL: str
    LLM_API_KEY: SecretStr
    LLM_MODEL: str
    LLM_TIMEOUT_SECONDS: float = Field(default=30, gt=0)  # how long one try may take
    LLM_MAX_RETRIES: int = Field(default=1, ge=0, le=3)  # tries after the first one (the client's own default is 2)
    LLM_TEMPERATURE: float = Field(default=0, ge=0, le=2)  # 0: the most likely words, the same answer every time

    # Answers (Session 8): which version of the prompt in app/prompts/answer/ to use
    ANSWER_PROMPT_VERSION: str = "v2"

    # The agent (Session 9): its prompt, and the limits on each patient message
    AGENT_PROMPT_VERSION: str = "v1"
    AGENT_MAX_STEPS: int = Field(default=5, ge=1, le=10)  # model calls per patient message, at most
    AGENT_TOKEN_BUDGET: int = Field(default=20000, gt=0)  # tokens per patient message, at most
    AGENT_HISTORY_MESSAGES: int = Field(default=30, ge=2)  # how many stored messages the model sees again

    # The clinic's data file: it must exist
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

    # The database: PostgreSQL only from Session 7 (search needs pgvector and full-text search)
    DATABASE_URL: str = Field(pattern=r"^postgresql\+asyncpg://")

    # Search (Session 7): the two models, and how many results each step keeps
    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-small"
    EMBEDDING_BATCH_SIZE: int = Field(default=32, gt=0)
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    SEARCH_CANDIDATES: int = Field(default=10, ge=5, le=100)  # from each search, before fusion
    RRF_K: int = Field(default=60, gt=0)  # Reciprocal Rank Fusion's constant
    SEARCH_TOP_K: int = Field(default=5, ge=1, le=20)  # how many results /search returns at most
    RERANK_THRESHOLD: float = Field(default=0.05, ge=0, le=1)  # measured with labs/threshold.py

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
