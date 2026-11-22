# app/services/answer.py
import logging

from app.core.config import Settings
from app.core.enums import Role
from app.prompts.system import CLINIC_ASSISTANT
from app.providers.llm.openai_compatible import OpenAICompatibleLLM

logger = logging.getLogger(__name__)


class AnswerService:
    """Answers a patient's question from the clinic's information."""

    def __init__(self, llm: OpenAICompatibleLLM, settings: Settings):
        self.llm = llm
        self.settings = settings
        # Read the clinic's information once, not on every question
        self.clinic_info = settings.CLINIC_INFO_PATH.read_text(encoding="utf-8")

    def answer(self, question: str) -> str:
        messages = [
            {"role": Role.SYSTEM, "content": CLINIC_ASSISTANT.format(clinic_info=self.clinic_info)},
            {"role": Role.USER, "content": question},
        ]
        reply = self.llm.chat(messages)

        if reply.tokens_in > self.settings.PROMPT_TOKENS_WARNING:
            logger.warning("Expensive question: %d tokens in", reply.tokens_in)
        return reply.text
