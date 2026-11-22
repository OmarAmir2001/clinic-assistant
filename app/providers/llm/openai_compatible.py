import logging
from dataclasses import dataclass

from openai import OpenAI, OpenAIError

from app.core.config import Settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """The language model could not give us an answer."""


@dataclass
class LLMReply:
    """What the model wrote, and what it cost."""
    text: str
    tokens_in: int
    tokens_out: int


class OpenAICompatibleLLM:
    """Talks to any OpenAI-compatible LLM server (Gemini, Ollama, ...)."""

    def __init__(self, settings: Settings):
        self.model = settings.LLM_MODEL
        self.client = OpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY.get_secret_value(),
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )

    def chat(self, messages: list[dict]) -> LLMReply:
        """Send a conversation to the model and return its reply."""
        try:
            response = self.client.chat.completions.create(model=self.model, messages=messages)
        except OpenAIError as error:
            logger.error("LLM call failed: %s", error)
            raise LLMError("The assistant is not available right now. Please try again later.") from error

        reply = LLMReply(
            text=response.choices[0].message.content,
            tokens_in=response.usage.prompt_tokens,
            tokens_out=response.usage.completion_tokens,
        )
        logger.info("LLM call done: %d tokens in, %d tokens out", reply.tokens_in, reply.tokens_out)
        return reply
