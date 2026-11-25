# app/services/ingestion.py
import logging
import uuid
from dataclasses import dataclass
from typing import BinaryIO

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.enums import DocumentType
from app.core.errors import ConflictError, EmptyDocumentError, NotFoundError
from app.db.models import Chunk, Document
from app.repositories.documents import DocumentInfo, DocumentRepository
from app.repositories.files import FileStore, StoredFile
from app.services.chunking import chunk_text
from app.services.cleaning import clean_text, looks_broken
from app.services.file_checks import check_content, detect_type, safe_display_name
from app.services.loaders import TextBlock, load_document

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReadFile:
    """A file that is saved on disk, checked, read and cut into chunks, but not in the database yet."""
    name: str
    type: DocumentType
    stored: StoredFile
    chunks: list[dict]


class IngestionService:
    """Upload, check, read, clean, chunk and save a clinic document (requirement FR-7).

    The order matters: the slow and risky work (saving, reading, chunking) happens first,
    then one short transaction writes everything, and only after it commits do we delete old files.
    """

    def __init__(self, files: FileStore, documents: DocumentRepository, session: AsyncSession, settings: Settings):
        self.files = files
        self.documents = documents
        self.session = session
        self.settings = settings

    async def ingest(self, filename: str | None, content: BinaryIO) -> tuple[DocumentInfo, bool]:
        """Returns the document and True if it is new, or the existing one and False if we already had this file."""
        read = await run_in_threadpool(self._save_and_read, filename, content)
        try:
            async with self.session.begin():
                # The same file again? Keep one copy and give back the one we have (the fingerprint decides)
                existing = await self.documents.get_by_sha256(read.stored.sha256)
                if existing is None:
                    document = Document(
                        id=uuid.uuid4(),
                        name=read.name,
                        type=read.type,
                        stored_as=read.stored.path.name,
                        size_bytes=read.stored.size_bytes,
                        sha256=read.stored.sha256,
                    )
                    # The document row and ALL its chunks in one transaction: never half a document
                    await self.documents.add(document, [{**c, "document_id": document.id} for c in read.chunks])
        except IntegrityError:
            # The same file was uploaded twice at the same moment: the other upload won
            self.files.delete(read.stored.path)
            existing = await self.documents.get_by_sha256(read.stored.sha256)
            if existing is None:
                raise
        except Exception:
            self.files.delete(read.stored.path)  # nothing in the database, so nothing on disk either
            raise

        if existing is not None:
            self.files.delete(read.stored.path)
            logger.info("Document %s uploaded again: returning the one we have", existing.id.hex)
            return (await self.documents.info([existing]))[0], False

        # Log ids and counts only, never the text: a document may contain personal data
        logger.info("Document %s ingested: %d chunks", document.id.hex, len(read.chunks))
        return (await self.documents.info([document]))[0], True

    async def replace(self, document_id: uuid.UUID, filename: str | None, content: BinaryIO) -> DocumentInfo:
        """Swap a document's file for a new version. If anything fails, the old version stays as it was."""
        # 1. Read the new file BEFORE touching the database. A bad file fails here, and nothing changes
        read = await run_in_threadpool(self._save_and_read, filename, content)
        try:
            async with self.session.begin():
                # 2. Lock the document's row, then swap the row's details and all its chunks together
                document = await self.documents.lock(document_id)
                if document is None:
                    raise NotFoundError(f"There is no document with id {document_id.hex}.")
                old_file = document.stored_as
                new_chunks = [{**c, "document_id": document.id} for c in read.chunks]
                await self.documents.replace_chunks(document.id, new_chunks)
                document.name = read.name
                document.type = read.type
                document.stored_as = read.stored.path.name
                document.size_bytes = read.stored.size_bytes
                document.sha256 = read.stored.sha256
        except IntegrityError as error:
            self.files.delete(read.stored.path)
            raise ConflictError("Another document already has exactly this content.") from error
        except Exception:
            self.files.delete(read.stored.path)
            raise

        # 3. Only now, after the commit, delete the old file: the database no longer points at it
        self.files.delete(self.files.folder / old_file)
        logger.info("Document %s replaced: %d chunks", document_id.hex, len(read.chunks))
        return (await self.documents.info([document]))[0]

    async def list_documents(self) -> list[DocumentInfo]:
        return await self.documents.info(await self.documents.all())

    async def get_chunks(self, document_id: uuid.UUID) -> list[Chunk]:
        if await self.documents.get(document_id) is None:
            raise NotFoundError(f"There is no document with id {document_id.hex}.")
        return await self.documents.chunks(document_id)

    def _save_and_read(self, filename: str | None, content: BinaryIO) -> ReadFile:
        """The slow part (Session 4's pipeline). It runs in a worker thread, outside any transaction."""
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

            # 4. Cut each block into chunks, so a chunk never mixes two pages or two sections
            chunks = []
            for block in blocks:
                broken = looks_broken(block.text)
                for text in chunk_text(block.text, self.settings.CHUNK_SIZE, self.settings.CHUNK_OVERLAP):
                    chunks.append(
                        {"position": len(chunks), "text": text, "page": block.page,
                         "section": block.section, "looks_broken": broken}
                    )
        except Exception:
            self.files.delete(stored.path)  # we keep nothing we rejected
            raise
        return ReadFile(name=name, type=doc_type, stored=stored, chunks=chunks)
