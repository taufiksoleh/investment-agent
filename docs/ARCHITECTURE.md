# Architecture

Investment Agent is a plugin-based backend for multi-asset investment
analysis, inspired by Netflix Dispatch's plugin pattern. The core app knows
only two things about any asset class: **its slug**, and **that it implements
`AssetAnalysisPlugin`**. It has zero knowledge of what "gold" or "stock"
actually means.

## Request flow

```
GET /analyze/gold
        │
        ▼
api/router.py: analyze_asset("gold")
        │
        ▼
plugins/registry.py: PluginRegistry.get("gold")
        │  (404 PluginNotFoundError if slug isn't registered)
        ▼
plugins/base.py: AssetAnalysisPlugin.analyze()   <- generic, same for every plugin
        │
        ├─ 1. await self.get_current_price()      -> plugins/gold/adapters.py
        │       InternalGoldPriceAdapter.fetch_price()
        │       └─ httpx call to the internal price API (shared/http_client.py)
        │       └─ returns a generic PriceSnapshot (never a GoldPrice)
        │
        ├─ 2. self.build_prompt(price_snapshot)    -> plugins/gold/prompts.py
        │       build_gold_prompt() composes a prompt embedding the verified
        │       price and asking for JSON-shaped reasoning back
        │
        ├─ 3. await self._agent_client.run_analysis(prompt) -> shared/agent_client.py
        │       ClaudeAgentClient wraps the Claude Agent SDK (with the
        │       WebSearch tool enabled) purely for REASONING - it never
        │       supplies price numbers, only context/news/causal explanation
        │
        └─ 4. self._parse_agent_response(price_snapshot, raw_response)
                merges the verified price with the agent's JSON reasoning
                into one AssetAnalysis - the shape returned by every plugin
        │
        ▼
AssetAnalysis JSON response
```

The critical invariant: **prices always come from step 1 (an internal
adapter), never from step 3 (the agent)**. The agent's web search tool is for
understanding *why* a price moved, not *what* the price is.

## The plugin contract

Defined once, in `plugins/base.py`:

```python
class AssetAnalysisPlugin(ABC):
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

A plugin author implements exactly two methods:

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

## Why plugin-based

- **The core app never grows.** Adding "stock" analysis shouldn't require
  touching the API layer, the shared HTTP/agent clients, or any existing
  plugin's code.
- **One endpoint, not N.** `/analyze/{asset_type}` scales to any number of
  asset classes without new routes.
- **Isolation.** A bug or a schema change in the gold plugin can't leak into
  the stock plugin — they share only the abstract contract and generic
  infrastructure in `shared/`.
- **Testability.** Every external dependency (HTTP client, agent client) is
  constructor-injected, so each plugin can be tested with fakes, without
  network access or an API key.

## Adding a new asset class (e.g. `stock`)

No existing file changes except `main.py`'s registration block. Concretely:

1. Create `src/investment_agent/plugins/stock/` with the same shape as `gold/`:
   - `models.py` — e.g. `StockPrice`, extending nothing special, plus
     `StockAnalysis(AssetAnalysis)` if stock needs extra output fields.
   - `adapters.py` — `InternalStockPriceAdapter`, calling whatever internal
     endpoint serves stock prices, returning a `PriceSnapshot`.
   - `prompts.py` — `build_stock_prompt(price_snapshot) -> str`.
   - `plugin.py` — `StockAnalysisPlugin(AssetAnalysisPlugin)` with
     `slug = "stock"`, implementing `get_current_price()` and
     `build_prompt()` by delegating to the adapter and prompt function above.
2. In `main.py`'s `_build_registry()`, instantiate the new adapter and
   plugin, and call `registry.register(stock_plugin)`.
3. Add `tests/plugins/stock/test_plugin.py` and `test_adapters.py` mirroring
   the gold tests.

That's it — `/analyze/stock` works immediately, `shared/` and `api/` are
untouched, and `plugins/base.py`'s contract guarantees the response shape
matches every other asset class.
