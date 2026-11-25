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

`main` always holds the latest session.

```bash
git clone <this repo>
cd clinic-assistant
git switch session-7
```

## This branch: Session 7, Hybrid Search & Reranking

You need Docker Desktop running and `DATABASE_URL` in `.env` (PostgreSQL is required from this session).
Download the two search models once, before class (about 2.7 GB):

```bash
uv sync
uv run python -m labs.download_models
```

The chunks table changed (embeddings and keyword search), so start fresh once, then upload the clinic's documents:

```bash
docker compose down -v
docker compose up -d db
uv run python -m app.db.setup
uv run fastapi dev
uv run python -m labs.upload_docs     # in a second terminal: the 7 files in data/clinic_docs/
```

Measure, then ask:

```bash
uv run python -m labs.search_eval     # hit@1, hit@5 and MRR for every search method
uv run python -m labs.threshold       # where to cut off "not relevant"
uv run python -m labs.ask "Do you take Allianz cards?"
```

You need Python 3.13 and [uv](https://docs.astral.sh/uv/). Never commit `.env`: it holds your API key (and, from Session 5, your database password).

