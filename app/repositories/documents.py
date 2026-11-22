# app/repositories/documents.py
from dataclasses import dataclass
from datetime import datetime

from app.core.enums import DocumentType


@dataclass(frozen=True)
class Document:
    """One uploaded file, and what we learned while reading it."""
    id: str
    name: str             # the cleaned name, for showing only
    type: DocumentType
    stored_as: str        # our random file name on disk
    size_bytes: int
    sha256: str           # a fingerprint of the content (Session 6 uses it to spot re-uploads)
    pages: int | None
    chunk_count: int
    warnings: tuple[str, ...]
    uploaded_at: datetime


@dataclass(frozen=True)
class Chunk:
    """One piece of a document, with where it came from."""
    document_id: str
    index: int
    text: str
    page: int | None
    section: str | None


class InMemoryDocumentRepository:
    """Keeps documents and chunks in dictionaries. A restart loses them all: Session 6 moves them to PostgreSQL."""

    def __init__(self):
        self._documents: dict[str, Document] = {}
        self._chunks: dict[str, list[Chunk]] = {}

    def add(self, document: Document, chunks: list[Chunk]) -> None:
        self._documents[document.id] = document
        self._chunks[document.id] = chunks

    def all(self) -> list[Document]:
        return sorted(self._documents.values(), key=lambda d: d.uploaded_at)

    def get(self, document_id: str) -> Document | None:
        return self._documents.get(document_id)

    def chunks(self, document_id: str) -> list[Chunk]:
        return self._chunks.get(document_id, [])
