# labs/download_models.py
"""Download the two search models once (about 2.7 GB), before class. After that they load from the cache.

    uv run python -m labs.download_models
"""
from app.core.config import get_settings
from app.providers.embeddings.e5 import E5Embeddings
from app.providers.rerankers.cross_encoder import CrossEncoderReranker

if __name__ == "__main__":
    settings = get_settings()
    embeddings = E5Embeddings(settings.EMBEDDING_MODEL, settings.EMBEDDING_BATCH_SIZE)
    reranker = CrossEncoderReranker(settings.RERANKER_MODEL)
    print(f"Embedding model ready: {settings.EMBEDDING_MODEL} ({embeddings.dimension} numbers per text)")
    print(f"Reranker ready: {settings.RERANKER_MODEL}")
    scores = reranker.score("Do you accept AXA?", ["We accept AXA, Allianz and MetLife.", "Brush your teeth."])
    print(f"A test: the right passage scores {scores[0]:.2f}, the wrong one {scores[1]:.2f}")
