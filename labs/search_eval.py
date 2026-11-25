# labs/search_eval.py
"""Measure search on questions whose answers we know (data/search_questions.json).

    uv run python -m labs.search_eval                  # every method we have
    uv run python -m labs.search_eval like --misses    # one method, and the questions it missed

hit@1: the right chunk came first. hit@5: it was in the top 5. MRR: 1/rank of the right chunk, averaged.
"""
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import Integer, cast, or_, select
from sqlalchemy.orm import joinedload

from app.core.config import get_settings
from app.db.database import make_engine, make_sessions
from app.db.models import Chunk
from app.providers.embeddings.e5 import E5Embeddings
from app.providers.rerankers.cross_encoder import CrossEncoderReranker
from app.repositories.chunks import ChunkRepository
from app.services.search import SearchService

QUESTIONS = json.loads(Path("data/search_questions.json").read_text(encoding="utf-8"))
METHODS = ["like", "words", "meaning", "hybrid", "reranked"]


async def by_like(session, question: str, limit: int) -> list[int]:
    """The first idea everyone has: chunks that contain any word of the question, most words first."""
    words = [w.strip("?؟.,!") for w in question.split() if len(w.strip("?؟.,!")) > 2]
    matched = sum(cast(Chunk.text.ilike(f"%{w}%"), Integer) for w in words)
    query = select(Chunk.id).where(or_(*(Chunk.text.ilike(f"%{w}%") for w in words)))
    return list(await session.scalars(query.order_by(matched.desc(), Chunk.id).limit(limit)))


async def ranking(method: str, service: SearchService, session, question: str) -> list[int]:
    if method == "like":
        return await by_like(session, question, 5)
    if method == "words":
        return await service.by_words(question, 5)
    if method == "meaning":
        return await service.by_meaning(question, 5)
    if method == "hybrid":
        return await service.hybrid(question, 5)
    return [hit.chunk.id for hit in await service.reranked(question)][:5]


async def main(methods: list[str], show_misses: bool) -> None:
    settings = get_settings()
    engine = make_engine(settings.DATABASE_URL)
    embeddings = E5Embeddings(settings.EMBEDDING_MODEL, settings.EMBEDDING_BATCH_SIZE)
    reranker = CrossEncoderReranker(settings.RERANKER_MODEL) if "reranked" in methods else None
    async with make_sessions(engine)() as session:
        rows = await session.execute(select(Chunk).options(joinedload(Chunk.document)))
        chunks = {c.id: c for c in rows.scalars()}
        service = SearchService(ChunkRepository(session), embeddings, reranker, settings)
        print(f"{len(QUESTIONS['questions'])} questions, {len(chunks)} chunks\n")
        print(f"{'method':<10} {'hit@1':>6} {'hit@5':>6} {'MRR':>6}")
        misses: dict[str, list[str]] = {}
        for method in methods:
            hit1 = hit5 = rr = 0.0
            for item in QUESTIONS["questions"]:
                ranked = await ranking(method, service, session, item["q"])
                rank = next((r for r, cid in enumerate(ranked, 1) if answers(chunks[cid], item["answers"])), None)
                hit1 += rank == 1
                hit5 += rank is not None
                rr += 1 / rank if rank else 0
                if rank != 1:
                    misses.setdefault(method, []).append(f"{item['q']}  (rank {rank or '-'})")
            n = len(QUESTIONS["questions"])
            print(f"{method:<10} {hit1 / n:>6.0%} {hit5 / n:>6.0%} {rr / n:>6.2f}")
        if show_misses:
            for method, lines in misses.items():
                print(f"\nNot first with {method}:")
                for line in lines:
                    print(f"  {line}")
    await engine.dispose()


def answers(chunk: Chunk, expected: list[list[str]]) -> bool:
    return any(chunk.document.name == name and words.lower() in chunk.text.lower() for name, words in expected)


if __name__ == "__main__":
    asked = [a for a in sys.argv[1:] if not a.startswith("--")] or METHODS
    asyncio.run(main(asked, "--misses" in sys.argv))
