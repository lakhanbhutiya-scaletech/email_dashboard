# Backend — FastAPI/uvicorn, dependencies managed by uv.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Install deps first (separate layer — cached unless lockfile changes).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Now copy the actual app code.
COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations
COPY run_server.py entrypoint.sh ./
RUN chmod +x entrypoint.sh

RUN uv sync --frozen --no-dev

EXPOSE 8090

# Runs migrations then starts uvicorn — see entrypoint.sh.
CMD ["./entrypoint.sh"]
