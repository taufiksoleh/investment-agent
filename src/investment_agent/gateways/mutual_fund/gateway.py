"""The mutual fund asset gateway.

Wires the mutual-fund-specific price adapter and prompt template into the
generic `analyze()` flow provided by the `Analyzable` use case. This class
supplies "what" data and "what" prompt, never "how" to run the analysis.
"""

from __future__ import annotations

from investment_agent.domain.models import PriceSnapshot
from investment_agent.gateways.mutual_fund.adapter import InternalMutualFundPriceAdapter
from investment_agent.gateways.mutual_fund.prompts import build_mutual_fund_prompt
from investment_agent.infrastructure.agent_client import ClaudeAgentClient
from investment_agent.infrastructure.exceptions import UpstreamPriceUnavailableError
from investment_agent.infrastructure.http_client import InternalApiClient
from investment_agent.use_cases.analyze_asset import Analyzable


class MutualFundGateway(Analyzable):
    """Gateway for one specific mutual fund, selected by BMoney product id.

    BMoney lists many funds; the product id configured on `price_adapter`
    (see `Settings.mutual_fund_product_id` for the default gateway, or a
    per-request id for `/analyze/mutual-fund/{product_id}`) determines
    which one this gateway represents - the same way `GoldGateway`
    represents one specific commodity.
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

    @classmethod
    def for_product(
        cls,
        product_id: int,
        agent_client: ClaudeAgentClient,
        http_client: InternalApiClient,
    ) -> MutualFundGateway:
        """Assemble a gateway for one BMoney product id.

        The one place that knows how to construct a `MutualFundGateway` -
        used both for the default gateway registered at startup
        (`main.py`, via `Settings.mutual_fund_product_id`) and for
        `/analyze/mutual-fund/{product_id}`'s per-request construction
        (`api/mutual_fund_router.py`), so there's a single construction
        path instead of each caller assembling the adapter by hand.
        """
        return cls(
            agent_client=agent_client,
            price_adapter=InternalMutualFundPriceAdapter(http_client, product_id=product_id),
        )

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
