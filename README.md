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

`main` always holds the latest session.

```bash
git clone <this repo>
cd clinic-assistant
git switch session-5
```

## This branch: Session 5, Data Modeling & Containers

You also need [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

```bash
cp .env.example .env              # then put your key and a database password in .env
docker compose up -d db           # start PostgreSQL in a container
uv run python -m app.db.setup     # create the tables, add the doctors and their slots
uv run fastapi dev
```

The log says `Connected to the database at localhost:5432`.

Or run the API in a container too:

```bash
docker compose up -d --build
docker compose exec api uv run python -m app.db.setup
```

You need Python 3.13 and [uv](https://docs.astral.sh/uv/). Never commit `.env`: it holds your API key (and, from Session 5, your database password).

