# app/core/enums.py
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


class Specialty(StrEnum):
    """The clinic's medical specialties."""
    DERMATOLOGY = "dermatology"
    PEDIATRICS = "pediatrics"
    INTERNAL_MEDICINE = "internal-medicine"
    DENTISTRY = "dentistry"


class Weekday(StrEnum):
    """Days of the week, starting from Saturday like the clinic's week."""
    SATURDAY = "saturday"
    SUNDAY = "sunday"
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
