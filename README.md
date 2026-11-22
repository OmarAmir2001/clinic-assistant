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

`main` always holds the latest session.

```bash
git clone <this repo>
cd clinic-assistant
git switch session-1
```

## This branch: Session 1, Problem-First & Why Naive AI Fails

Create a file named `.env` in this folder (it is ignored by git):

```
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_API_KEY=paste-your-key-here
LLM_MODEL=gemini-flash-latest
```

Then run the four attempts:

```bash
uv run ask.py
```

You need Python 3.13 and [uv](https://docs.astral.sh/uv/). Never commit `.env`: it holds your API key.

