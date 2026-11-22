# app/api/schemas/documents.py
from datetime import datetime

from pydantic import BaseModel

from app.core.enums import DocumentType

# Our document ids: 32 hexadecimal characters
DOCUMENT_ID_PATTERN = r"^[0-9a-f]{32}$"


class DocumentOut(BaseModel):
    """What staff see about an uploaded document. Our file name on disk is never sent back."""
    id: str
    name: str
    type: DocumentType
    size_bytes: int
    pages: int | None
    chunks: int
    warnings: list[str]
    uploaded_at: datetime


class ChunkOut(BaseModel):
    index: int
    text: str
    characters: int
    page: int | None
    section: str | None
