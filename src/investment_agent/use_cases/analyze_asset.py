"""The analysis use case: fetch a verified price, reason about it via a
`ReasoningAgent` (Claude Agent SDK, Google ADK + any OpenAI-compatible
endpoint, ...), and merge both into one `AssetAnalysis`.

`Analyzable` is the port a gateway implements to opt into this use case - it
extends the `AssetGateway` port (`get_current_price()`) with `build_prompt()`,
and provides `analyze()` as the generic flow every asset class shares.
`analyze()` itself is never overridden - it's what guarantees every asset
class produces the same `AssetAnalysis` shape through the same steps, which
is what lets `/analyze/{asset_type}` stay a single generic endpoint.
"""

import json
import re
from abc import ABC, abstractmethod

from investment_agent.domain.models import AssetAnalysis, PriceSnapshot
from investment_agent.infrastructure.exceptions import AgentResponseParsingError
from investment_agent.use_cases.reasoning_agent import ReasoningAgent

# Models routinely wrap JSON answers in a markdown fence (```json ... ```)
# even when told to return raw JSON; strip that before parsing.
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```$", re.DOTALL)


class Analyzable(ABC):
    """Mixin a gateway inherits from to support `/analyze/{asset_type}`.

    Subclasses supply "what" data to use and "what" prompt to reason with;
    they never override `analyze()` itself, which stays identical for every
    asset class so the API layer can treat all gateways interchangeably.
    """

    #: Unique identifier used in the URL (`/analyze/{slug}`) and by the registry.
    slug: str
    #: Human-readable name, e.g. for logging or future UI use.
    display_name: str

    def __init__(self, agent_client: ReasoningAgent) -> None:
        # Injected rather than constructed here, so tests can supply a fake.
        self._agent_client = agent_client

    @abstractmethod
    async def get_current_price(self) -> PriceSnapshot:
        """Fetch this asset's current price from its own internal data source.

        Must never call out to the Claude Agent SDK or web search - price
        numbers are only ever trusted from an internal adapter.
        """

    @abstractmethod
    def build_prompt(self, price_snapshot: PriceSnapshot) -> str:
        """Compose the reasoning prompt for this asset class.

        The prompt must instruct the agent to return a JSON object whose keys
        match `AssetAnalysis`'s reasoning fields (key_drivers,
        technical_summary, fundamental_summary, recommendation,
        confidence_level, risk_scenario) - `current_price` and
        `price_change_pct` are filled in from `price_snapshot`, not the agent.
        """

    async def analyze(self) -> AssetAnalysis:
        """Run the generic analysis flow: fetch price -> build prompt -> reason -> merge.

        Identical for every gateway by design - only `get_current_price()` and
        `build_prompt()` vary per asset class.
        """
        price_snapshot = await self.get_current_price()
        prompt = self.build_prompt(price_snapshot)
        raw_response = await self._agent_client.run_analysis(prompt)
        return self._parse_agent_response(price_snapshot, raw_response)

    def _parse_agent_response(
        self, price_snapshot: PriceSnapshot, raw_response: str
    ) -> AssetAnalysis:
        """Merge the verified price with the agent's reasoning JSON into one `AssetAnalysis`."""
        stripped = raw_response.strip()
        fence_match = _CODE_FENCE_RE.match(stripped)
        json_text = fence_match.group(1) if fence_match else stripped

        try:
            reasoning = json.loads(json_text)
        except json.JSONDecodeError as exc:
            context_start = max(exc.pos - 100, 0)
            context = json_text[context_start : exc.pos + 100] or "<empty>"
            raise AgentResponseParsingError(
                f"Agent response for '{self.slug}' was not valid JSON: {exc}. "
                f"Text around the error: {context!r}"
            ) from exc

        try:
            return AssetAnalysis(
                current_price=price_snapshot.price,
                price_change_pct=price_snapshot.change_pct,
                **reasoning,
            )
        except (TypeError, ValueError) as exc:
            # TypeError: reasoning wasn't a mapping (e.g. a JSON array).
            # ValueError: covers pydantic's ValidationError (a ValueError
            # subclass) for a well-formed but wrong-shaped reasoning object
            # (missing key, bad enum value, confidence_level out of range).
            raise AgentResponseParsingError(
                f"Agent response for '{self.slug}' did not match the expected schema: {exc}"
            ) from exc
