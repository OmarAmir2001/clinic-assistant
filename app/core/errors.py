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


class UnsupportedFileError(AppError):
    """The file is not one of the types we accept, or its content doesn't match its name."""

    code = "unsupported_file"


class FileTooLargeError(AppError):
    """The file is bigger than the upload limit."""

    code = "file_too_large"


class EmptyDocumentError(AppError):
    """The file was accepted, but no text could be read from it."""

    code = "empty_document"
