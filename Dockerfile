FROM python:3.13-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/

FROM base AS builder

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    /uv/bin/uv sync --frozen --no-install-project --no-dev

FROM base AS development

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    /uv/bin/uv sync --frozen --no-install-project

COPY manage.py conftest.py ./
COPY app/ ./app/
COPY scripts/ ./scripts/

RUN chmod +x /app/scripts/*.sh

ENV PATH="/uv/bin:/app/.venv/bin:$PATH"

ENTRYPOINT ["/app/scripts/entrypoint.sh"]

FROM base AS production

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/uv/bin:/app/.venv/bin:$PATH"

COPY manage.py ./
COPY app/ ./app/
COPY scripts/ ./scripts/

RUN chmod +x /app/scripts/*.sh

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
