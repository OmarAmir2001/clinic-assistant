# app/core/errors.py
class AppError(Exception):
    """A problem we expect and can explain to the caller in one safe sentence."""

    code = "app_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    """The thing the caller asked for does not exist (or is not theirs)."""

    code = "not_found"


class ConflictError(AppError):
    """The request clashes with the current state, like a slot that is already booked."""

    code = "conflict"


class UnavailableError(AppError):
    """An outside service we depend on is not answering."""

    code = "unavailable"
