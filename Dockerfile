# Dockerfile: the recipe for our API's image
FROM python:3.13-slim

# 1. The tool that installs our packages
RUN pip install uv

# 2. Inside the image, our project lives in /app
WORKDIR /app

# 3. The package list first, then install the packages
COPY pyproject.toml uv.lock ./
RUN uv sync --locked

# 4. Then our code
COPY . .

# 5. What runs when a container starts
CMD ["uv", "run", "fastapi", "run", "app/main.py", "--port", "8000"]
