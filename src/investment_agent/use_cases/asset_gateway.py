"""The port every asset gateway must implement.

This is the minimal contract the core app depends on for any asset class: a
slug, a display name, and a way to fetch a verified current price. It says
nothing about analysis, news, or any other capability - those are separate
ports (see `analyze_asset.py`, and future use cases) that a gateway opts
into independently by also inheriting from them.
"""

from typing import Protocol, runtime_checkable

from investment_agent.domain.models import PriceSnapshot


@runtime_checkable
class AssetGateway(Protocol):
    """Structural port: anything with this shape can be registered as a gateway."""

    slug: str
    display_name: str

    async def get_current_price(self) -> PriceSnapshot:
        """Fetch this asset's current price from its own internal data source.

        Must never call out to the Claude Agent SDK or web search - price
        numbers are only ever trusted from an internal adapter.
        """
        ...
