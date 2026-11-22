from enum import StrEnum


class LogLevel(StrEnum):
    """How much the app writes to its log."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Role(StrEnum):
    """Who is speaking in a conversation with the model."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
