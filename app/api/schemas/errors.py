# app/api/schemas/errors.py
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    field: str
    problem: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = []


class ErrorResponse(BaseModel):
    """Every error the API returns has this one shape."""
    error: ErrorBody


# Add this to a router's `responses` so /docs shows our real error shape for bad input
INVALID_INPUT = {422: {"model": ErrorResponse, "description": "Some fields are missing or invalid"}}
