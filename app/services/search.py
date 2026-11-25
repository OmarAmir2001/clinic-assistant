# app/services/search.py
import logging
from collections import defaultdict
from dataclasses import dataclass

from fastapi.concurrency import run_in_threadpool

from app.core.config import Settings
from app.db.models import Chunk
from app.providers.embeddings.base import EmbeddingProvider
from app.providers.rerankers.base import Reranker
from app.repositories.chunks import ChunkRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchHit:
    chunk: Chunk
    score: float  # the reranker's score: how well this chunk answers the question (0 to 1)


@dataclass(frozen=True)
class SearchResult:
    hits: list[SearchHit]  # good enough to show, best first; empty means "nothing found"
    best_score: float | None  # the best score even if it was too low (useful for measuring)


def reciprocal_rank_fusion(*rankings: list[int], k: int) -> list[int]:
    """Merge ranked lists of chunk ids. Each list gives a chunk 1 / (k + its rank); the sums decide.

    Only the ranks count, never the raw scores, so lists with very different scores can be merged.
    """
    scores: dict[int, float] = defaultdict(float)
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] += 1 / (k + rank)
    return sorted(scores, key=scores.__getitem__, reverse=True)


class SearchService:
    """Find the chunks that answer a question: words + meaning, fused, then reranked and cut off."""

    def __init__(self, chunks: ChunkRepository, embeddings: EmbeddingProvider, reranker: Reranker, settings: Settings):
        self.chunks = chunks
        self.embeddings = embeddings
        self.reranker = reranker
        self.settings = settings

    async def by_words(self, question: str, limit: int) -> list[int]:
        return [chunk_id for chunk_id, _ in await self.chunks.by_words(question, limit)]

    async def by_meaning(self, question: str, limit: int) -> list[int]:
        # The model is slow Python work: run it in a worker thread, like PDF reading in Session 6
        [vector] = await run_in_threadpool(self.embeddings.embed_queries, [question])
        return [chunk_id for chunk_id, _ in await self.chunks.by_meaning(vector, limit)]

    async def hybrid(self, question: str, limit: int) -> list[int]:
        words = await self.by_words(question, limit)
        meaning = await self.by_meaning(question, limit)
        return reciprocal_rank_fusion(words, meaning, k=self.settings.RRF_K)[:limit]

    async def reranked(self, question: str) -> list[SearchHit]:
        # 1. A wide net: the best candidates from both searches, fused
        candidates = await self.hybrid(question, self.settings.SEARCH_CANDIDATES)
        if not candidates:
            return []
        # 2. The reranker reads each candidate together with the question and scores it
        chunks = await self.chunks.get_many(candidates)
        scores = await run_in_threadpool(self.reranker.score, question, [chunks[i].text for i in candidates])
        hits = [SearchHit(chunks[i], s) for i, s in zip(candidates, scores, strict=True)]
        return sorted(hits, key=lambda hit: hit.score, reverse=True)

    async def search(self, question: str, top_k: int) -> SearchResult:
        ranked = await self.reranked(question)
        if not ranked:
            return SearchResult(hits=[], best_score=None)
        # 3. Keep only what passes the threshold we measured: better "nothing found" than a wrong chunk
        hits = [hit for hit in ranked if hit.score >= self.settings.RERANK_THRESHOLD][:top_k]
        logger.info("Search: %d candidates, %d above the threshold, best score %.3f",
                    len(ranked), len(hits), ranked[0].score)
        return SearchResult(hits=hits, best_score=ranked[0].score)
