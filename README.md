# Clinic Booking Assistant

Lab code for **AI Engineering with Python**, Program 1 (Training Unit, Higher Institute for Computer Science and Information Systems).

Nile Family Clinic is fictional. This is an educational prototype, not a medical system.

## One branch per session

Each session continues from the one before it.

| Branch | Session |
| --- | --- |
| `session-1` | Session 1: Problem-First & Why Naive AI Fails |
| `session-2` | Session 2: Lightweight Design & Clean Architecture |
| `session-3` | Session 3: API Contracts & Validation |
| `session-4` | Session 4: Secure Document Ingestion & Chunking |
| `session-5` | Session 5: Data Modeling & Containers |
| `session-6` | Session 6: Reliable Pipelines & Safe Booking (Checkpoint 1) |
| `session-7` | Session 7: Hybrid Search & Reranking |
| `session-8` | Session 8: Grounded Answers & Structured Outputs |

`main` always holds the latest session.

```bash
git clone <this repo>
cd clinic-assistant
git switch session-8
```

## This branch: Session 8, Grounded Answers & Structured Outputs

`POST /answer` searches the clinic's documents first, gives the model only what it found, and returns the answer
with its sources, or an honest "I don't know". Session 2's `/chat` is gone: Session 9 brings chat back as an agent.

Pick a model in `.env` (see `.env.example`): Gemini in the cloud, or Ollama on your laptop:

```bash
ollama pull qwen2.5:3b              # only for the local block
uv run fastapi dev
uv run python -m labs.answer "Do you take Allianz cards?"
uv run python -m labs.answer_check  # 14 questions: the right source, or "I don't know"
```

The prompts live in `app/prompts/answer/<version>/`. To try a new one, copy a folder, change it, and set
`ANSWER_PROMPT_VERSION` in `.env`. Measure before and after with `labs/answer_check.py`.

The database and the documents are the same as Session 7 (if you're starting fresh, follow Session 7's steps first).

You need Python 3.13 and [uv](https://docs.astral.sh/uv/). Never commit `.env`: it holds your API key (and, from Session 5, your database password).

