FROM python:3.12-slim AS base

# uv gives us fast, reproducible installs from the committed lockfile.
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /usr/local/bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-install-project --no-dev || uv sync --no-install-project --no-dev

COPY src ./src
COPY README.md ./
RUN uv sync --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "investment_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
