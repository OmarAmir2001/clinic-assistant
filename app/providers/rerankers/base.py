# app/providers/rerankers/base.py
from typing import Protocol


class Reranker(Protocol):
    """Anything that scores (question, passage) pairs. Higher means a better answer."""

    def score(self, query: str, passages: list[str]) -> list[float]: ...
