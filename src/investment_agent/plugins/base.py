"""The contract every asset-class plugin must implement.

This is the one file the core app and every plugin both depend on. It defines
what a plugin IS (a slug + a way to get a price + a way to build a prompt) and
what happens when it's analyzed - so adding a new asset class never requires
touching the API layer, only writing a new plugin against this same contract.
"""

import json
import re
from abc import ABC, abstractmethod
from datetime import UTC, datetime

from investment_agent.shared.agent_client import ClaudeAgentClient
from investment_agent.shared.base_models import AssetAnalysis, AssetNews, PriceSnapshot
from investment_agent.shared.exceptions import AgentResponseParsingError, NewsNotSupportedError

# Models routinely wrap JSON answers in a markdown fence (```json ... ```)
# even when told to return raw JSON; strip that before parsing.
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```$", re.DOTALL)


class AssetAnalysisPlugin(ABC):
    """Base class for all asset-class plugins (gold, stock, mutual_fund, ...).

    Subclasses supply "what" data to use and "what" prompt to reason with;
    they never override `analyze()` itself, which stays identical for every
    asset class so the API layer can treat all plugins interchangeably.
    """

    #: Unique identifier used in the URL (`/analyze/{slug}`) and by the registry.
    slug: str
    #: Human-readable name, e.g. for logging or future UI use.
    display_name: str

    def __init__(self, agent_client: ClaudeAgentClient) -> None:
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

    def build_news_prompt(self, price_snapshot: PriceSnapshot) -> str:
        """Compose the prompt asking the agent for recent news about this asset.

        Opt-in: unlike `get_current_price()`/`build_prompt()`, a plugin isn't
        required to override this. The default raises `NewsNotSupportedError`,
        which the API layer turns into a 404 for `/analyze/{slug}/news`.
        """
        raise NewsNotSupportedError(self.slug)

    async def analyze(self) -> AssetAnalysis:
        """Run the generic analysis flow: fetch price -> build prompt -> reason -> merge.

        Identical for every plugin by design - only `get_current_price()` and
        `build_prompt()` vary per asset class.
        """
        price_snapshot = await self.get_current_price()
        prompt = self.build_prompt(price_snapshot)
        raw_response = await self._agent_client.run_analysis(prompt)
        return self._parse_agent_response(price_snapshot, raw_response)

    async def get_news(self) -> AssetNews:
        """Run the generic news flow: fetch price (for context) -> build news
        prompt -> reason via web search -> parse into `AssetNews`.

        Raises `NewsNotSupportedError` (via `build_news_prompt()`) for any
        plugin that hasn't opted in.
        """
        price_snapshot = await self.get_current_price()
        prompt = self.build_news_prompt(price_snapshot)
        raw_response = await self._agent_client.run_analysis(prompt)
        return self._parse_news_response(raw_response)

    def _parse_news_response(self, raw_response: str) -> AssetNews:
        """Parse the agent's news JSON into an `AssetNews`, tagged with this plugin's slug."""
        stripped = raw_response.strip()
        fence_match = _CODE_FENCE_RE.match(stripped)
        json_text = fence_match.group(1) if fence_match else stripped

        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as exc:
            snippet = raw_response[:200] or "<empty>"
            raise AgentResponseParsingError(
                f"News response for '{self.slug}' was not valid JSON: {exc}. "
                f"Raw response started with: {snippet!r}"
            ) from exc

        try:
            return AssetNews(
                slug=self.slug,
                generated_at=datetime.now(UTC),
                **parsed,
            )
        except (TypeError, ValueError) as exc:
            raise AgentResponseParsingError(
                f"News response for '{self.slug}' did not match the expected schema: {exc}"
            ) from exc

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
            snippet = raw_response[:200] or "<empty>"
            raise AgentResponseParsingError(
                f"Agent response for '{self.slug}' was not valid JSON: {exc}. "
                f"Raw response started with: {snippet!r}"
            ) from exc

        try:
            return AssetAnalysis(
                current_price=price_snapshot.price,
                price_change_pct=price_snapshot.change_pct,
                **reasoning,
            )
        except TypeError as exc:
            raise AgentResponseParsingError(
                f"Agent response for '{self.slug}' did not match the expected schema: {exc}"
            ) from exc
