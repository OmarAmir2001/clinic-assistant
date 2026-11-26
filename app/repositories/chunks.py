# app/repositories/chunks.py
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import Chunk

ARABIC_WORD = re.compile(r"[\u0600-\u06FF]+")
LATIN_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*")


def words_query(question: str):
    """The question's words as a full-text query that matches ANY of them (OR).

    Each language's words go to its own dictionary: English drops "what", "is", "the" and stems
    "tests" to "test"; Arabic stems "التحاليل" to "تحاليل". websearch_to_tsquery never fails on odd input.
    """
    english = " or ".join(LATIN_WORD.findall(question))
    arabic = " or ".join(ARABIC_WORD.findall(question))
    return func.websearch_to_tsquery("english", english).op("||")(func.websearch_to_tsquery("arabic", arabic))


class ChunkRepository:
    """Every search question about chunks. Each method returns (chunk id, score), best first."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def by_words(self, question: str, limit: int) -> list[tuple[int, float]]:
        """Keyword search: chunks that contain the question's words, ranked by PostgreSQL's ts_rank."""
        query = words_query(question)
        rank = func.ts_rank(Chunk.words, query)
        rows = await self.session.execute(
            select(Chunk.id, rank).where(Chunk.words.op("@@")(query)).order_by(rank.desc()).limit(limit)
        )
        return [(chunk_id, float(score)) for chunk_id, score in rows]

    async def by_meaning(self, vector: list[float], limit: int) -> list[tuple[int, float]]:
        """Vector search: the chunks whose embeddings are closest to the question's (cosine distance, via HNSW)."""
        distance = Chunk.embedding.cosine_distance(vector)
        rows = await self.session.execute(
            select(Chunk.id, distance).where(Chunk.embedding.is_not(None)).order_by(distance).limit(limit)
        )
        return [(chunk_id, 1 - float(d)) for chunk_id, d in rows]  # similarity = 1 - distance

    async def get_many(self, ids: list[int]) -> dict[int, Chunk]:
        """The chunks themselves, with their document, for the ids search picked."""
        rows = await self.session.scalars(select(Chunk).where(Chunk.id.in_(ids)).options(joinedload(Chunk.document)))
        return {chunk.id: chunk for chunk in rows}
