# app/api/errors.py
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError, ConflictError, NotFoundError, UnavailableError

logger = logging.getLogger(__name__)

# Which HTTP status code each kind of app error becomes
STATUS_FOR = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    UnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


def error_response(status_code: int, code: str, message: str, details: list | None = None) -> JSONResponse:
    """Build the one error shape every endpoint uses."""
    body = {"error": {"code": code, "message": message, "details": details or []}}
    return JSONResponse(status_code=status_code, content=body)


async def app_error_handler(request: Request, error: AppError) -> JSONResponse:
    status_code = next((s for kind, s in STATUS_FOR.items() if isinstance(error, kind)), 400)
    return error_response(status_code, error.code, error.message)


async def validation_error_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    # Name the field and the problem, but never echo the value: it may be a phone number
    details = [
        {"field": ".".join(str(part) for part in problem["loc"][1:]), "problem": problem["msg"]}
        for problem in error.errors()
    ]
    return error_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT, "validation_error", "Some fields are missing or invalid.", details
    )


async def http_error_handler(request: Request, error: StarletteHTTPException) -> JSONResponse:
    # Errors FastAPI raises itself, like a URL that doesn't exist (404) or a wrong method (405)
    return error_response(error.status_code, "http_error", str(error.detail))


async def unexpected_error_handler(request: Request, error: Exception) -> JSONResponse:
    logger.exception("Unexpected error on %s %s", request.method, request.url.path)
    return error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_error", "Something went wrong on our side. Please try again."
    )


def add_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
