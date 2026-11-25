# app/providers/embeddings/base.py
from typing import Protocol


class EmbeddingProvider(Protocol):
    """Anything that turns text into vectors. The search code depends on this, never on one model.

    Questions and passages are embedded by two different methods on purpose: some models (like E5)
    need to be told which is which, and the provider, not the caller, is responsible for that.
    """

    dimension: int  # how many numbers in each vector

    def embed_queries(self, texts: list[str]) -> list[list[float]]: ...

    def embed_passages(self, texts: list[str]) -> list[list[float]]: ...
