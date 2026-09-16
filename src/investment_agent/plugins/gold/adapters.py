"""Adapter between the internal gold price API and the generic plugin flow.

This is the ONLY place in the gold plugin allowed to know the internal API's
URL shape and payload format - `plugin.py` just calls `fetch_price()`.
"""

from investment_agent.plugins.gold.models import GoldPrice
from investment_agent.shared.base_models import PriceSnapshot
from investment_agent.shared.http_client import InternalApiClient


class InternalGoldPriceAdapter:
    """Fetches the current gold price from the internal price API."""

    def __init__(self, http_client: InternalApiClient, endpoint: str = "/prices/gold") -> None:
        self._http_client = http_client
        self._endpoint = endpoint

    async def fetch_price(self) -> PriceSnapshot:
        """Fetch and normalize the internal API's gold payload into a `PriceSnapshot`.

        Normalizing here (instead of in the plugin) is what lets
        `AssetAnalysisPlugin.analyze()` stay asset-agnostic: it only ever
        deals with `PriceSnapshot`, never `GoldPrice`.
        """
        payload = await self._http_client.get_json(self._endpoint)
        gold_price = GoldPrice.model_validate(payload)
        return PriceSnapshot(
            price=gold_price.price_usd_per_ounce,
            change_pct=gold_price.change_pct_24h,
            currency="USD",
            as_of=gold_price.as_of,
        )
