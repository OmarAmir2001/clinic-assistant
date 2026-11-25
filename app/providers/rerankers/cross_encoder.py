# app/providers/rerankers/cross_encoder.py
import logging

from sentence_transformers import CrossEncoder
from torch.nn import Sigmoid

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """A cross-encoder reads the question and one passage together, word against word.

    Slower than comparing two vectors, so we only use it on the few candidates search already found.
    The mMARCO model was trained on questions and passages in 14 languages, Arabic among them.
    """

    def __init__(self, model_name: str):
        logger.info("Loading the reranker %s", model_name)
        # Sigmoid turns the model's raw output into a score between 0 and 1, so a threshold means the same
        # thing for every reranker we might switch to
        self.model = CrossEncoder(model_name, device="cpu", activation_fn=Sigmoid())

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        # A score between 0 and 1 for each pair: how well this passage answers this question
        return self.model.predict([(query, p) for p in passages]).tolist()
