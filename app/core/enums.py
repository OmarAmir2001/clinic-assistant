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
    TOOL = "tool"  # a tool's result, sent back to the model (Session 9)


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


class DocumentType(StrEnum):
    """The only kinds of file the clinic may upload (an allowlist)."""
    PDF = "pdf"
    TXT = "txt"
    MD = "md"


class AppointmentStatus(StrEnum):
    """Where a booking stands. A cancelled booking stays in the table, so its history is kept."""
    BOOKED = "booked"
    CANCELLED = "cancelled"


class ToolName(StrEnum):
    """The six things the agent may ask our code to do (Session 9)."""
    SEARCH_CLINIC_DOCS = "search_clinic_docs"
    LIST_DOCTORS = "list_doctors"
    CHECK_AVAILABILITY = "check_availability"
    BOOK_APPOINTMENT = "book_appointment"
    GET_APPOINTMENT = "get_appointment"
    CANCEL_OR_RESCHEDULE = "cancel_or_reschedule"


class ChangeAction(StrEnum):
    """What cancel_or_reschedule should do with an appointment."""
    CANCEL = "cancel"
    RESCHEDULE = "reschedule"
