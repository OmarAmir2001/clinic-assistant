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
| `session-10` | Session 10: Streaming UI & Build-It Capstone (Capstone 1) |

`main` always holds the latest session.

```bash
git clone <this repo>
cd clinic-assistant
git switch session-10
```

## This branch: Session 10, Streaming UI & Build-It Capstone

`POST /chat/stream` is the same agent as `POST /chat`, but as Server-Sent Events: the patient sees what it is doing
("Looking up free times…"), then the answer as the model writes it. `ui/app.py` is a chat page in Streamlit: step
progress, the sources it read, a confirmation card with Yes / No buttons, document upload for staff, and clear
messages when the server or the model is down. `labs/trace.py` reads a conversation back from the database, tool call
by tool call: that is how we find where an answer went wrong.

No database change since Session 9. In two terminals:

```bash
uv run fastapi dev                            # the API
uv run python -m streamlit run ui/app.py      # the chat page: http://localhost:8501
```

And from the terminal:

```bash
uv run python -m labs.stream "Which dermatologist is free on Sunday?"   # every event, with the second it came
uv run python -m labs.trace                                            # the newest conversation, step by step
uv run python -m labs.booking_flow                                     # Session 9's 7 checks, still passing
```

Capstone 1 (what each pair presents) is in [`docs/capstone-1.md`](docs/capstone-1.md).

You need Python 3.13 and [uv](https://docs.astral.sh/uv/). Never commit `.env`: it holds your API key (and, from Session 5, your database password).

