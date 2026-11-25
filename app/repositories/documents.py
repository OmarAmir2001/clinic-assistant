# app/repositories/documents.py
import uuid
from dataclasses import dataclass

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, Document


@dataclass(frozen=True)
class DocumentInfo:
    """A document plus what we work out from its chunks (we don't store these twice: Session 5, 3NF)."""
    document: Document
    chunks: int
    pages: int | None
    warnings: list[str]


class DocumentRepository:
    """Every database question about documents and their chunks."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, document_id: uuid.UUID) -> Document | None:
        return await self.session.get(Document, document_id)

    async def lock(self, document_id: uuid.UUID) -> Document | None:
        query = select(Document).where(Document.id == document_id).with_for_update()
        return await self.session.scalar(query)

    async def get_by_sha256(self, sha256: str) -> Document | None:
        return await self.session.scalar(select(Document).where(Document.sha256 == sha256))

    async def all(self) -> list[Document]:
        return list(await self.session.scalars(select(Document).order_by(Document.uploaded_at)))

    async def add(self, document: Document, chunks: list[dict]) -> None:
        self.session.add(document)
        await self.session.flush()  # send the document's INSERT now: the chunks point at it
        await self.session.execute(insert(Chunk), chunks)  # one bulk INSERT for all the chunks

    async def replace_chunks(self, document_id: uuid.UUID, chunks: list[dict]) -> None:
        await self.session.execute(delete(Chunk).where(Chunk.document_id == document_id))
        await self.session.execute(insert(Chunk), chunks)

    async def chunks(self, document_id: uuid.UUID) -> list[Chunk]:
        query = select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.position)
        return list(await self.session.scalars(query))

    async def info(self, documents: list[Document]) -> list[DocumentInfo]:
        """Chunk counts, pages and warnings for many documents in two queries, not two per document."""
        ids = [d.id for d in documents]
        counts = await self.session.execute(
            select(Chunk.document_id, func.count(Chunk.id), func.max(Chunk.page))
            .where(Chunk.document_id.in_(ids))
            .group_by(Chunk.document_id)
        )
        totals = {doc_id: (count, pages) for doc_id, count, pages in counts}
        broken = await self.session.execute(
            select(Chunk.document_id, Chunk.page, Chunk.section)
            .where(Chunk.document_id.in_(ids), Chunk.looks_broken)
            .distinct()
            .order_by(Chunk.document_id, Chunk.page)
        )
        warnings: dict[uuid.UUID, list[str]] = {}
        for doc_id, page, section in broken:
            where = f"Page {page}" if page else f"Section '{section or 'start'}'"
            warnings.setdefault(doc_id, []).append(f"{where}: the Arabic text looks broken; check it by hand.")
        return [
            DocumentInfo(d, totals.get(d.id, (0, None))[0], totals.get(d.id, (0, None))[1], warnings.get(d.id, []))
            for d in documents
        ]
