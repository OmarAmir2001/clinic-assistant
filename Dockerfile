# Dockerfile
# The recipe for the API's image: Python, uv, our locked dependencies, then our code.
FROM python:3.13-slim

# uv, copied from its official image. A fixed version, so every build is the same
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

# Dependencies first. Docker reuses this layer until pyproject.toml or uv.lock change
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Then our code and the clinic's files, which change more often
COPY app ./app
COPY data ./data

# Don't run as root: a user that owns only the uploads folder
RUN useradd --create-home clinic && mkdir -p data/uploads && chown clinic data/uploads
USER clinic

EXPOSE 8000
CMD ["/app/.venv/bin/fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
