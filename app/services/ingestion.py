# app/services/ingestion.py
import logging
import uuid
from datetime import UTC, datetime
from typing import BinaryIO

from app.core.config import Settings
from app.core.errors import EmptyDocumentError, NotFoundError
from app.repositories.documents import Chunk, Document, InMemoryDocumentRepository
from app.repositories.files import FileStore
from app.services.chunking import chunk_text
from app.services.cleaning import clean_text, looks_broken
from app.services.file_checks import check_content, detect_type, safe_display_name
from app.services.loaders import TextBlock, load_document

logger = logging.getLogger(__name__)


class IngestionService:
    """Upload, check, read, clean and chunk a clinic document (requirement FR-7)."""

    def __init__(self, files: FileStore, documents: InMemoryDocumentRepository, settings: Settings):
        self.files = files
        self.documents = documents
        self.settings = settings

    def ingest(self, filename: str | None, content: BinaryIO) -> Document:
        # 1. Check the name: a clean name to show, and a type from the allowlist
        name = safe_display_name(filename)
        doc_type = detect_type(name)

        # 2. Save under our own random name, with the size limit enforced while writing
        stored = self.files.save(content, suffix=f".{doc_type}")
        try:
            # 3. Check the content really matches the type, then read and clean it
            check_content(stored.path, doc_type)
            blocks = load_document(stored.path, doc_type, self.settings.MAX_PDF_PAGES)
            blocks = [TextBlock(clean_text(b.text), b.page, b.section) for b in blocks]
            blocks = [b for b in blocks if b.text]
            if not blocks:
                raise EmptyDocumentError("No text could be read from this file. Scanned PDFs are not supported yet.")
        except Exception:
            self.files.delete(stored.path)  # we keep nothing we rejected
            raise

        # 4. Cut each block into chunks, so a chunk never mixes two pages or two sections
        document_id = uuid.uuid4().hex
        chunks = []
        for block in blocks:
            for text in chunk_text(block.text, self.settings.CHUNK_SIZE, self.settings.CHUNK_OVERLAP):
                chunks.append(Chunk(document_id, index=len(chunks), text=text, page=block.page, section=block.section))

        # 5. Some PDFs come out broken. We can't fix that here, but we can say so loudly
        warnings = tuple(
            f"{_where(b)}: the Arabic text looks broken; check it by hand." for b in blocks if looks_broken(b.text)
        )

        document = Document(
            id=document_id,
            name=name,
            type=doc_type,
            stored_as=stored.path.name,
            size_bytes=stored.size_bytes,
            sha256=stored.sha256,
            pages=max((b.page or 0) for b in blocks) or None,
            chunk_count=len(chunks),
            warnings=warnings,
            uploaded_at=datetime.now(UTC),
        )
        self.documents.add(document, chunks)
        # Log ids and counts only, never the text: a document may contain personal data
        logger.info("Document %s ingested: %d chunks, %d warnings", document.id, len(chunks), len(warnings))
        return document

    def list_documents(self) -> list[Document]:
        return self.documents.all()

    def get_chunks(self, document_id: str) -> list[Chunk]:
        if self.documents.get(document_id) is None:
            raise NotFoundError(f"There is no document with id {document_id}.")
        return self.documents.chunks(document_id)


def _where(block: TextBlock) -> str:
    return f"Page {block.page}" if block.page else f"Section '{block.section or 'start'}'"
