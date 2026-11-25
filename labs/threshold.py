# labs/threshold.py
"""Choose the relevance threshold from measurements, not from a guess.

    uv run python -m labs.threshold

For every question we know the answer to, and for questions the clinic's documents can't answer,
look at the best score search gives. A good threshold keeps the first group and drops the second.
"""
import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.config import get_settings
from app.db.database import make_engine, make_sessions
from app.db.models import Chunk
from app.providers.embeddings.e5 import E5Embeddings
from app.providers.rerankers.cross_encoder import CrossEncoderReranker
from app.repositories.chunks import ChunkRepository
from app.services.search import SearchService

QUESTIONS = json.loads(Path("data/search_questions.json").read_text(encoding="utf-8"))
THRESHOLDS = [0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5]


async def main() -> None:
    settings = get_settings()
    engine = make_engine(settings.DATABASE_URL)
    embeddings = E5Embeddings(settings.EMBEDDING_MODEL, settings.EMBEDDING_BATCH_SIZE)
    reranker = CrossEncoderReranker(settings.RERANKER_MODEL)
    async with make_sessions(engine)() as session:
        repository = ChunkRepository(session)
        service = SearchService(repository, embeddings, reranker, settings)
        await session.scalars(select(Chunk).options(joinedload(Chunk.document)))  # load the chunks once

        answered, unanswerable = [], []  # (best reranker score, best cosine similarity, question)
        for item in QUESTIONS["questions"]:
            best = (await service.reranked(item["q"]))[0]
            right = any(best.chunk.document.name == n and w.lower() in best.chunk.text.lower()
                        for n, w in item["answers"])
            if right:  # only questions where the first result is the right answer
                answered.append((best.score, await best_similarity(service, repository, item["q"]), item["q"]))
        for q in QUESTIONS["out_of_scope"]:
            best = (await service.reranked(q))[0]
            unanswerable.append((best.score, await best_similarity(service, repository, q), q))

    print("Best score per question (reranker 0-1 | cosine similarity of the closest chunk)")
    for title, group in (("Answerable, and search found the answer:", answered),
                         ("Not answerable from the documents:", unanswerable)):
        print(f"\n{title}")
        for score, similarity, q in sorted(group, reverse=True):
            print(f"  {score:5.3f} | {similarity:5.3f}  {q}")

    print("\nthreshold   answers kept   'nothing found' when right")
    for t in THRESHOLDS:
        kept = sum(s >= t for s, _, _ in answered) / len(answered)
        refused = sum(s < t for s, _, _ in unanswerable) / len(unanswerable)
        print(f"  {t:4.2f}         {kept:5.0%}          {refused:5.0%}")
    await engine.dispose()


async def best_similarity(service: SearchService, repository: ChunkRepository, question: str) -> float:
    [vector] = service.embeddings.embed_queries([question])
    return (await repository.by_meaning(vector, 1))[0][1]


if __name__ == "__main__":
    asyncio.run(main())
