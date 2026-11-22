import logging
import sys

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.providers.llm.openai_compatible import LLMError, OpenAICompatibleLLM
from app.services.answer import AnswerService

logger = logging.getLogger("app.main")


def main():
    # 1. Settings first: if anything is missing, stop here with a clear message
    try:
        settings = get_settings()
    except ValidationError as error:
        # Show only the setting's name and the problem, never the values (they may be secrets)
        problems = [f"  {problem['loc'][0]}: {problem['msg']}" for problem in error.errors()]
        sys.exit("Configuration error. Check your .env file:\n" + "\n".join(problems))

    # 2. Then logging, then the pieces of the app
    setup_logging(settings.LOG_LEVEL)
    llm = OpenAICompatibleLLM(settings)
    service = AnswerService(llm, settings)
    logger.info("%s is ready", settings.APP_NAME)

    # 3. A simple terminal chat. In Session 3, an API replaces this part.
    print("Ask the clinic a question (press Enter on an empty line to quit).")
    while True:
        question = input("> ").strip()
        if not question:
            break
        try:
            print(service.answer(question))
        except LLMError as error:
            print(error)


if __name__ == "__main__":
    main()
