# Architecture

Investment Agent is a Clean-Architecture-style backend for multi-asset
investment analysis: dependencies point inward (entities ← use cases ←
gateways ← infrastructure), and the core app knows only two things about any
asset class: **its slug**, and **that its gateway implements the
`Analyzable` use case's port**. It has zero knowledge of what "gold" or
"stock" actually means.

This shape is the same "core knows only the contract, concrete
implementations plug into it" pattern used by projects like
[Netflix Dispatch](https://github.com/Netflix/dispatch)'s plugin system -
here it's named with Clean Architecture vocabulary (entities, use cases,
gateways, infrastructure) instead of "plugin", since that's the terminology
this team already works in. See the "Naming" section below for why, and
what stays true either way.

## Layers

```
src/investment_agent/
  domain/         # Entities: PriceSnapshot, AssetAnalysis, Recommendation - pure
                    data, no framework or IO dependencies.
  use_cases/       # Ports + generic flows: AssetGateway (the minimal port every
                     asset must implement), Analyzable (the analysis use case).
  gateways/         # Interface adapters: one package per asset class (gold/, ...),
                      each implementing the use-case ports against a real upstream
                      API, plus the registry that looks gateways up by slug.
  api/               # Controllers: FastAPI routes + middleware.
  infrastructure/     # Frameworks & drivers: the reasoning agent clients
                        (Claude Agent SDK, Google ADK + DeepSeek) and the
                        factory that picks between them, the internal HTTP
                        client, structlog config, Settings.
```

## Request flow

```
GET /analyze/gold
        │
        ▼
api/router.py: analyze_asset("gold")
        │
        ▼
gateways/registry.py: GatewayRegistry.get("gold")
        │  (404 GatewayNotFoundError if slug isn't registered)
        ▼
use_cases/analyze_asset.py: Analyzable.analyze()   <- generic, same for every gateway
        │
        ├─ 1. await self.get_current_price()      -> gateways/gold/adapter.py
        │       InternalGoldPriceAdapter.fetch_price()
        │       └─ httpx call to the price API (infrastructure/http_client.py) -
        │          currently BMoney's public bullion price API (GET /bullion/prices),
        │          configured via INTERNAL_PRICE_API_URL
        │       └─ returns a generic PriceSnapshot (never a raw GoldPriceEntry)
        │
        ├─ 2. self.build_prompt(price_snapshot)    -> gateways/gold/prompts.py
        │       build_gold_prompt() composes a prompt embedding the verified
        │       price and asking for JSON-shaped reasoning back
        │
        ├─ 3. await self._agent_client.run_analysis(prompt) -> infrastructure/agent_client_factory.py
        │       build_agent_client(settings) returns whichever backend
        │       Settings.agent_provider selects - AdkAgentClient (Google
        │       ADK + any OpenAI-compatible endpoint via LiteLLM, default,
        │       no web search) or ClaudeAgentClient (Claude Agent SDK, with
        │       WebSearch) - purely for REASONING; it never supplies price
        │       numbers, only context/news/causal explanation
        │
        └─ 4. self._parse_agent_response(price_snapshot, raw_response)
                merges the verified price with the agent's JSON reasoning
                into one AssetAnalysis - the shape returned by every gateway
        │
        ▼
AssetAnalysis JSON response
```

The critical invariant: **prices always come from step 1 (an internal
adapter), never from step 3 (the agent)**. The agent's web search tool is for
understanding *why* a price moved, not *what* the price is. This invariant
holds regardless of what any future use case (news, a chatbot, ...) looks
like - anything that needs a price asks a gateway for it, never the LLM.

## The use-case ports

The minimal port every gateway implements, in `use_cases/asset_gateway.py`:

```python
class AssetGateway(Protocol):
    slug: str
    display_name: str
    async def get_current_price(self) -> PriceSnapshot: ...
```

The analysis use case, in `use_cases/analyze_asset.py`:

```python
class Analyzable(ABC):
    slug: str
    display_name: str

    @abstractmethod
    async def get_current_price(self) -> PriceSnapshot: ...

    @abstractmethod
    def build_prompt(self, price_snapshot: PriceSnapshot) -> str: ...

    async def analyze(self) -> AssetAnalysis:
        # generic flow - NOT overridden by subclasses
        ...
```

A gateway author implements exactly two methods:

- **`get_current_price()`** — fetch the asset's price from wherever that
  asset class's internal API lives, and normalize it into a `PriceSnapshot`.
- **`build_prompt()`** — compose the reasoning prompt, given the verified
  price. The prompt must ask the agent to return JSON matching
  `AssetAnalysis`'s reasoning fields (`key_drivers`, `technical_summary`,
  `fundamental_summary`, `recommendation`, `confidence_level`,
  `risk_scenario`).

`analyze()` itself is never overridden — it's what guarantees every asset
class produces the same `AssetAnalysis` shape through the same steps, which
is what lets `/analyze/{asset_type}` stay a single generic endpoint.

`Analyzable.__init__` takes an `agent_client: ReasoningAgent`
(`use_cases/reasoning_agent.py`) — the port for step 3 above:

```python
class ReasoningAgent(Protocol):
    async def run_analysis(self, prompt: str) -> str: ...
```

Gateways and `Analyzable` only ever depend on this port, never on
`ClaudeAgentClient` or `AdkAgentClient` directly — which backend actually
implements it is decided once, in `infrastructure/agent_client_factory.py`,
from `Settings.agent_provider`:

- **`openai_compatible`** (default) — `AdkAgentClient`
  (`infrastructure/adk_agent_client.py`), Google ADK's `LlmAgent` +
  `InMemoryRunner`, with the model routed through LiteLLM's generic
  `openai/<model>` custom-provider form to whatever OpenAI-compatible
  endpoint `OPENAI_COMPATIBLE_BASE_URL` points at — DeepSeek, Qwen, Zhipu
  GLM, Moonshot Kimi, a self-hosted vLLM/Ollama server, or any other
  provider that speaks the OpenAI chat-completions API
  (`OPENAI_COMPATIBLE_API_KEY`, `OPENAI_COMPATIBLE_MODEL`). Much cheaper
  than Claude; has no web search tool — ADK's built-in `google_search`
  grounding only works with Gemini models, and wiring a separate search API
  for an arbitrary endpoint is out of scope for now, so this backend
  reasons from the prompt text alone.
- **`claude`** — `ClaudeAgentClient` (`infrastructure/agent_client.py`),
  the Claude Agent SDK, with the `WebSearch` tool enabled
  (`INVESTMENT_AGENT_ANTHROPIC_API_KEY`).

Swapping providers is a one-line env var change (`AGENT_PROVIDER`); nothing
in `gateways/`, `use_cases/`, or `api/` needs to know which one is active.

Each use case is independent: adding a future one (e.g. a `NewsCapable`
port for a `/analyze/{asset_type}/news` endpoint) means adding a new file
under `use_cases/`, never editing `analyze_asset.py`. A gateway opts in by
also inheriting from that use case's port; `GatewayRegistry.require(slug,
Port)` looks up a gateway and asserts it implements a given port, raising
`UseCaseNotSupportedError` (404) when it doesn't - so a controller for any
future use case can stay generic without forcing every gateway to
implement every capability.

## Why this shape

- **The core app never grows for a new asset class.** Adding "stock"
  analysis shouldn't require touching the API layer, the infrastructure
  clients, or any existing gateway's code.
- **One endpoint, not N.** `/analyze/{asset_type}` scales to any number of
  asset classes without new routes.
- **Isolation.** A bug or a schema change in the gold gateway can't leak
  into the stock gateway — they share only the use-case ports and generic
  infrastructure.
- **Testability.** Every external dependency (HTTP client, agent client) is
  constructor-injected, so each gateway can be tested with fakes, without
  network access or an API key.

## Adding a new asset class (e.g. `stock`)

No existing file changes except `main.py`'s registration block. Concretely:

1. Create `src/investment_agent/gateways/stock/` with the same shape as
   `gold/`:
   - `models.py` — e.g. `StockPrice`, extending nothing special, plus
     `StockAnalysis(AssetAnalysis)` if stock needs extra output fields.
   - `adapter.py` — `InternalStockPriceAdapter`, calling whatever internal
     endpoint serves stock prices, returning a `PriceSnapshot`.
   - `prompts.py` — `build_stock_prompt(price_snapshot) -> str`.
   - `gateway.py` — `StockGateway(Analyzable)` with `slug = "stock"`,
     implementing `get_current_price()` and `build_prompt()` by delegating
     to the adapter and prompt function above.
2. In `main.py`'s `_build_registry()`, instantiate the new adapter and
   gateway, and call `registry.register(stock_gateway)`.
3. Add `tests/gateways/stock/test_gateway.py` and `test_adapter.py`
   mirroring the gold tests.

That's it — `/analyze/stock` works immediately, `infrastructure/` and
`api/` are untouched, and `Analyzable`'s contract guarantees the response
shape matches every other asset class.

(Dynamic gateway discovery via Python entry points - so `main.py` wouldn't
need editing at all - is a deliberate non-goal for now: with a handful of
in-house asset classes and one team, an explicit registration list is
clearer than the indirection. Revisit if/when there's a genuine 5th+ asset
or an external contributor.)

## Naming: why "gateway"/"use case", not "plugin"

Earlier versions of this codebase used "plugin" vocabulary throughout
(`AssetAnalysisPlugin`, `PluginRegistry`, `plugins/`). The shape never
changed - this is still dependency inversion: use cases depend on an
abstract port, concrete gateways implement it, nothing in the use-case
layer imports a concrete gateway. What changed is the vocabulary, to match
Clean Architecture's layer names (entities/use cases/interface
adapters/frameworks & drivers), which this team already uses day to day.
If you're coming from the plugin-era code or docs, the mapping is direct:
`AssetAnalysisPlugin` → `AssetGateway` (the port) + `Analyzable` (the
analysis use case), `plugins/gold/` → `gateways/gold/`, `PluginRegistry` →
`GatewayRegistry`, `shared/` → `infrastructure/`.
