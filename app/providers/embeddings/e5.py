# app/providers/embeddings/e5.py
import logging

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class E5Embeddings:
    """multilingual-e5: Arabic and English text in one vector space, small enough for a laptop CPU.

    E5 was trained with a prefix on every text: "query: " for questions, "passage: " for the
    text being searched. Without the prefixes it still runs, but finds worse matches.
    """

    QUERY_PREFIX = "query: "
    PASSAGE_PREFIX = "passage: "

    def __init__(self, model_name: str, batch_size: int):
        logger.info("Loading the embedding model %s", model_name)
        self.model = SentenceTransformer(model_name, device="cpu")
        self.dimension = self.model.get_embedding_dimension()
        self.batch_size = batch_size

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return self._embed([self.QUERY_PREFIX + t for t in texts])

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return self._embed([self.PASSAGE_PREFIX + t for t in texts])

    def _embed(self, texts: list[str]) -> list[list[float]]:
        # Many texts per call (a batch) is much faster than one at a time.
        # normalize: every vector gets length 1, so cosine similarity is a simple dot product.
        vectors = self.model.encode(texts, batch_size=self.batch_size, normalize_embeddings=True)
        return vectors.tolist()
