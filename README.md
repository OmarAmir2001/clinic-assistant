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

`main` always holds the latest session.

```bash
git clone <this repo>
cd clinic-assistant
git switch session-6
```

## This branch: Session 6, Reliable Pipelines & Safe Booking (Checkpoint 1)

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) running, and `DATABASE_URL` in `.env`
pointing at PostgreSQL (see `.env.example`). Coming from Session 5? The tables changed, so start fresh once:

```bash
docker compose down -v            # delete the old database (development only!)
docker compose up -d db
uv run python -m app.db.setup     # the new tables, the doctors and two weeks of slots
uv run fastapi dev
```

Then, in a second terminal, break it on purpose:

```bash
uv run python -m labs.rush        # 20 patients book the same slot at the same moment
uv run python -m labs.retry       # the same request arrives twice
uv run python -m labs.crash       # a two-step change fails in the middle
uv run python -m labs.check_all   # every promise the API makes (Checkpoint 1)
```

You need Python 3.13 and [uv](https://docs.astral.sh/uv/). Never commit `.env`: it holds your API key (and, from Session 5, your database password).

