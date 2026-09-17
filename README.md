# Investment Agent

[![CI](https://github.com/taufiksoleh/investment-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/taufiksoleh/investment-agent/actions/workflows/ci.yml)

Clean-Architecture-style backend API for multi-asset investment analysis
(starting with gold), combining verified prices from an internal API with
reasoning from a pluggable LLM backend.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the use-case/gateway
contract, request flow, and how to add a new asset class.

## Stack

- Python 3.12+, FastAPI (async)
- Reasoning backend, switchable via `AGENT_PROVIDER`:
  - `deepseek` (default) - Google ADK, routed through LiteLLM to DeepSeek's
    OpenAI-compatible API. Much cheaper than Claude; no web search tool.
  - `claude` - the Claude Agent SDK, with web search enabled.
- httpx for internal price API calls
- Pydantic v2 for schemas/validation
- uv for dependency management
- pytest + pytest-asyncio for testing
- Docker / docker-compose for local dev

## Setup

```bash
cp .env.example .env   # fill in DEEPSEEK_API_KEY (or set AGENT_PROVIDER=claude
                        # and fill in INVESTMENT_AGENT_ANTHROPIC_API_KEY) and
                        # INTERNAL_PRICE_API_URL
uv sync
```

## Run locally

```bash
uv run uvicorn investment_agent.main:app --reload
```

Then:

```bash
curl http://localhost:8000/analyze/gold
curl http://localhost:8000/healthz
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
The `gateways/gold/` folder is the template to copy.
