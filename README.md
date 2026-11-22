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

`main` always holds the latest session.

```bash
git clone <this repo>
cd clinic-assistant
git switch session-4
```

## This branch: Session 4, Secure Document Ingestion & Chunking

```bash
cp .env.example .env      # then put your own key in .env
uv run fastapi dev
```

Open http://127.0.0.1:8000/docs and try `POST /documents` with a PDF, TXT or MD file.

You need Python 3.13 and [uv](https://docs.astral.sh/uv/). Never commit `.env`: it holds your API key.

