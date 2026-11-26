# app/prompts/loader.py
from dataclasses import dataclass
from pathlib import Path
from string import Template

from app.core.enums import Role

# Every prompt lives in its own folder, one sub-folder per version: app/prompts/<name>/<version>/
PROMPTS_DIR = Path(__file__).parent


@dataclass(frozen=True)
class Prompt:
    """One version of one prompt: the rules (the system message) and the user message, with blanks."""
    name: str
    version: str
    rules: Template  # may have blanks too, like $calendar (Session 9)
    question: Template  # blanks look like $evidence and $question

    def system(self, **values: str) -> dict:
        """The rules, as the system message. A blank left empty is an error, not a silent gap."""
        return {"role": Role.SYSTEM, "content": self.rules.substitute(values)}

    def user(self, **values: str) -> dict:
        """The user message, its blanks filled."""
        return {"role": Role.USER, "content": self.question.substitute(values)}

    def messages(self, **values: str) -> list[dict]:
        """The two messages for the model: the rules, then the user message."""
        return [self.system(**values), self.user(**values)]


def load_prompt(name: str, version: str) -> Prompt:
    """Read a prompt's files once, at startup. A missing version stops the app with a clear message."""
    folder = PROMPTS_DIR / name / version
    if not folder.is_dir():
        raise FileNotFoundError(f"There is no prompt folder app/prompts/{name}/{version}")
    return Prompt(
        name=name,
        version=version,
        rules=Template((folder / "rules.md").read_text(encoding="utf-8").strip()),
        question=Template((folder / "question.md").read_text(encoding="utf-8").strip()),
    )
