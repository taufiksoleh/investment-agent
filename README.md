# Investment Agent

Plugin-based backend API for multi-asset investment analysis (starting with
gold), combining verified prices from an internal API with reasoning from the
Claude Agent SDK.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the plugin contract,
request flow, and how to add a new asset class.

## Stack

- Python 3.12+, FastAPI (async)
- Claude Agent SDK for reasoning + web search
- httpx for internal price API calls
- Pydantic v2 for schemas/validation
- uv for dependency management
- pytest + pytest-asyncio for testing
- Docker / docker-compose for local dev

## Setup

```bash
cp .env.example .env   # fill in ANTHROPIC_API_KEY and INTERNAL_PRICE_API_URL
uv sync
```

## Run locally

```bash
uv run uvicorn investment_agent.main:app --reload
```

Then:

```bash
curl http://localhost:8000/analyze/gold
```

## Run with Docker

```bash
docker compose up --build
```

## Tests

```bash
uv run pytest
```

## Lint

```bash
uv run ruff check .
```

## Adding a new asset class

See "Adding a new asset class" in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
The `gold/` plugin folder is the template to copy.
