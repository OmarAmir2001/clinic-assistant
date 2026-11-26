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
| `session-9` | Session 9: Building the Clinic Agent |

`main` always holds the latest session.

```bash
git clone <this repo>
cd clinic-assistant
git switch session-9
```

## This branch: Session 9, Building the Clinic Agent

`POST /chat` is an agent. The model picks one of six tools (search the documents, list the doctors, check the free
times, book, look up, cancel or move); our code checks the arguments, runs the tool and sends the result back, in a
loop with limits. The conversation is saved in PostgreSQL, so "book the second one" works. A booking, cancelling or
moving never runs when the model asks: the patient sees the details (read from the database) and must reply "yes".

The `messages` and `conversations` tables changed, so start the database fresh, then upload the documents again:

```bash
docker compose down -v
docker compose up -d db
uv run python -m app.db.setup
uv run fastapi dev
uv run python -m labs.upload_docs
```

Then talk to the agent:

```bash
uv run python -m labs.first_call "Which dermatologist is free on Sunday?"   # what the model asks for (nothing runs)
uv run python -m labs.chat                                                 # a conversation; an empty line ends it
uv run python -m labs.booking_flow                                         # policy, schedule, confirm, book: 7 checks
uv run python -m labs.stubborn_llm   # a pretend model that never stops asking for tools (set LLM_BASE_URL to try it)
```

The agent's rules live in `app/prompts/agent/<version>/`; its limits (`AGENT_MAX_STEPS`, `AGENT_TOKEN_BUDGET`,
`AGENT_HISTORY_MESSAGES`) in `.env`. `POST /answer` from Session 8 is still there.

You need Python 3.13 and [uv](https://docs.astral.sh/uv/). Never commit `.env`: it holds your API key (and, from Session 5, your database password).

