"""The gold asset-analysis plugin.

Wires the gold-specific price adapter and prompt template into the generic
`analyze()` flow defined by `AssetAnalysisPlugin`. This class supplies "what"
data and "what" prompt, never "how" to run the analysis.
"""

from investment_agent.domain.models import PriceSnapshot
from investment_agent.gateways.base import AssetAnalysisPlugin
from investment_agent.gateways.gold.adapters import InternalGoldPriceAdapter
from investment_agent.gateways.gold.prompts import build_gold_prompt
from investment_agent.infrastructure.agent_client import ClaudeAgentClient


class GoldAnalysisPlugin(AssetAnalysisPlugin):
    """Asset-analysis plugin for physical/spot gold."""

    slug = "gold"
    display_name = "Gold"

    def __init__(
        self,
        agent_client: ClaudeAgentClient,
        price_adapter: InternalGoldPriceAdapter,
    ) -> None:
        super().__init__(agent_client)
        self._price_adapter = price_adapter

    async def get_current_price(self) -> PriceSnapshot:
        return await self._price_adapter.fetch_price()

    def build_prompt(self, price_snapshot: PriceSnapshot) -> str:
        return build_gold_prompt(price_snapshot)
