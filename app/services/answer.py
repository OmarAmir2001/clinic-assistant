# app/services/answer.py
import logging
import re
from dataclasses import dataclass

from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.db.models import Chunk
from app.prompts.loader import Prompt
from app.providers.llm.openai_compatible import OpenAICompatibleLLM
from app.services.search import SearchHit, SearchService

logger = logging.getLogger(__name__)

ARABIC = re.compile("[ء-ي]")  # any Arabic letter, from ء to ي
DONT_KNOW = {
    "en": "I don't know. The clinic's documents don't answer this. The reception can help you.",
    "ar": "لا أعرف. مستندات العيادة لا تجيب عن هذا السؤال، ويمكن لموظفي الاستقبال مساعدتك.",
}


class ModelAnswer(BaseModel):
    """The form the model must fill in. Its JSON schema is sent with the question."""
    answer: str = Field(description="The reply to the patient, in the patient's language")
    sources: list[int] = Field(description="The numbers of the evidence the answer uses, like [1, 3]")
    answered: bool = Field(description="false if the evidence does not answer the question")


@dataclass(frozen=True)
class GroundedAnswer:
    text: str
    answered: bool
    sources: list[Chunk]  # the chunks the answer came from, checked by our code


def dont_know(question: str) -> GroundedAnswer:
    language = "ar" if ARABIC.search(question) else "en"
    return GroundedAnswer(text=DONT_KNOW[language], answered=False, sources=[])


def source_label(chunk: Chunk) -> str:
    """Where a chunk comes from, as a person would say it: 'lab_tests.md › Blood tests'."""
    where = chunk.section or (f"page {chunk.page}" if chunk.page else None)
    return f"{chunk.document.name} › {where}" if where else chunk.document.name


def number_evidence(hits: list[SearchHit]) -> str:
    """Give every chunk a number, so the model can point at it: [1], [2], ..."""
    return "\n\n".join(
        f"[{n}] {source_label(hit.chunk)}\n{hit.chunk.text}" for n, hit in enumerate(hits, start=1)
    )


def checked_sources(numbers: list[int], hits: list[SearchHit]) -> list[Chunk]:
    """Keep only the numbers that point at real evidence, each once, in the model's order."""
    unknown = [n for n in numbers if not 1 <= n <= len(hits)]
    if unknown:
        logger.warning("The model cited evidence that doesn't exist: %s (there were %d)", unknown, len(hits))
    valid = [n for n in dict.fromkeys(numbers) if n not in unknown]  # dict.fromkeys: each number once, in order
    return [hits[n - 1].chunk for n in valid]


class AnswerService:
    """Answers a patient's question from the clinic's documents, and says where each answer came from."""

    def __init__(self, search: SearchService, llm: OpenAICompatibleLLM, prompt: Prompt, settings: Settings):
        self.search = search
        self.llm = llm
        self.prompt = prompt
        self.settings = settings

    async def answer(self, question: str) -> GroundedAnswer:
        # 1. Search first: the evidence
        result = await self.search.search(question, self.settings.SEARCH_TOP_K)

        # 2. Nothing found? Then there is nothing to answer from: don't call the model at all
        if not result.hits:
            logger.info("Nothing found for the question: answered without the model")
            return dont_know(question)

        # 3. The rules, the numbered evidence and the question, from the prompt's files
        messages = self.prompt.messages(evidence=number_evidence(result.hits), question=question)

        # 4. The model fills in the form (slow network work: in a worker thread)
        form, reply = await run_in_threadpool(self.llm.fill_form, messages, ModelAnswer)
        if reply.tokens_in > self.settings.PROMPT_TOKENS_WARNING:
            logger.warning("Expensive question: %d tokens in", reply.tokens_in)

        # 5. Our code checks the form: every claim needs a real source
        sources = checked_sources(form.sources, result.hits)
        if not form.answered:
            return GroundedAnswer(text=form.answer, answered=False, sources=[])
        if not sources:
            logger.warning("An answer without a valid source was replaced by 'I don't know'")
            return dont_know(question)
        return GroundedAnswer(text=form.answer, answered=True, sources=sources)
