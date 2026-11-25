# app/db/embed_all.py
"""Embed chunks that have no embedding yet, in batches. Run it after changing the embedding model, too.

    uv run python -m app.db.embed_all           # only the chunks without an embedding
    uv run python -m app.db.embed_all --again   # every chunk (after you change EMBEDDING_MODEL)
"""
import asyncio
import sys

from sqlalchemy import update

from app.core.config import get_settings
from app.db.database import make_engine, make_sessions
from app.db.models import Chunk
from app.providers.embeddings.e5 import E5Embeddings
from app.repositories.chunks import ChunkRepository

BATCH = 64


async def main(again: bool) -> None:
    settings = get_settings()
    embeddings = E5Embeddings(settings.EMBEDDING_MODEL, settings.EMBEDDING_BATCH_SIZE)
    engine = make_engine(settings.DATABASE_URL)
    done = 0
    async with make_sessions(engine)() as session:
        if again:
            async with session.begin():
                await session.execute(update(Chunk).values(embedding=None))
        repository = ChunkRepository(session)
        while True:
            async with session.begin():
                chunks = await repository.without_embedding(BATCH)
            if not chunks:
                break
            vectors = embeddings.embed_passages([c.text for c in chunks])  # slow: outside any transaction
            async with session.begin():  # one transaction per batch: a crash keeps the batches already done
                for chunk, vector in zip(chunks, vectors, strict=True):
                    chunk.embedding = vector
            done += len(chunks)
            print(f"  {done} chunks embedded")
    await engine.dispose()
    print(f"Done: {done} chunks.")


if __name__ == "__main__":
    asyncio.run(main(again="--again" in sys.argv))
