"""The mutual fund asset gateway.

Wires the mutual-fund-specific price adapter and prompt template into the
generic `analyze()` flow provided by the `Analyzable` use case. This class
supplies "what" data and "what" prompt, never "how" to run the analysis.
"""

from investment_agent.domain.models import PriceSnapshot
from investment_agent.gateways.mutual_fund.adapter import InternalMutualFundPriceAdapter
from investment_agent.gateways.mutual_fund.prompts import build_mutual_fund_prompt
from investment_agent.infrastructure.agent_client import ClaudeAgentClient
from investment_agent.infrastructure.exceptions import UpstreamPriceUnavailableError
from investment_agent.use_cases.analyze_asset import Analyzable


class MutualFundGateway(Analyzable):
    """Gateway for one specific mutual fund, selected by ISIN code.

    BMoney's products endpoint lists many funds; the ISIN configured on
    `price_adapter` (see `Settings.mutual_fund_isin_code`) determines which
    one this gateway represents - the same way `GoldGateway` represents one
    specific commodity.
    """

    slug = "mutual-fund"
    display_name = "Mutual Fund"

    def __init__(
        self,
        agent_client: ClaudeAgentClient,
        price_adapter: InternalMutualFundPriceAdapter,
    ) -> None:
        super().__init__(agent_client)
        self._price_adapter = price_adapter

    async def get_current_price(self) -> PriceSnapshot:
        return await self._price_adapter.fetch_price()

    def build_prompt(self, price_snapshot: PriceSnapshot) -> str:
        # Set by get_current_price() (via fetch_price()), always called
        # immediately before build_prompt() by Analyzable.analyze().
        product = self._price_adapter.last_product
        if product is None:
            raise UpstreamPriceUnavailableError(
                f"{self.slug}: build_prompt() called before get_current_price()."
            )
        return build_mutual_fund_prompt(price_snapshot, product)
