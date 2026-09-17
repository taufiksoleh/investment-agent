"""Adapter between the gold price API and the generic plugin flow.

This is the ONLY place in the gold plugin allowed to know the price API's
URL shape and payload format - `plugin.py` just calls `fetch_price()`.
Currently backed by BMoney's public bullion price API
(`GET https://api.bmoney.id/bullion/prices`), which is IDR-per-gram already,
so no currency conversion is needed.
"""

from investment_agent.domain.models import PriceSnapshot
from investment_agent.gateways.gold.models import BullionPriceResponse, GoldPriceEntry
from investment_agent.infrastructure.exceptions import UpstreamPriceUnavailableError
from investment_agent.infrastructure.http_client import InternalApiClient


class InternalGoldPriceAdapter:
    """Fetches the current gold price from the bullion price API.

    The API's `period` query param accepts: "one_week", "one_month",
    "three_month", "one_year", "all_time" - all return the same daily-OHLC
    shape, just over a longer window. No auth is required for this endpoint
    (verified directly); it's read-only public bullion price data.
    """

    def __init__(
        self,
        http_client: InternalApiClient,
        endpoint: str = "/bullion/prices",
        period: str = "one_week",
    ) -> None:
        self._http_client = http_client
        self._endpoint = endpoint
        # "one_week" (not just today) so there are always at least two daily
        # entries to derive a 24h change_pct from.
        self._period = period

    async def fetch_price(self) -> PriceSnapshot:
        """Fetch daily bullion prices and normalize the latest one into a `PriceSnapshot`.

        Normalizing here (instead of in the plugin) is what lets
        `AssetAnalysisPlugin.analyze()` stay asset-agnostic: it only ever
        deals with `PriceSnapshot`, never the raw bullion API shape.
        """
        payload = await self._http_client.get_json(self._endpoint, params={"period": self._period})
        response = BullionPriceResponse.model_validate(payload)
        if not response.data:
            raise UpstreamPriceUnavailableError(
                "Bullion price API returned no data for the gold price series."
            )

        latest = response.data[-1]
        change_pct = self._calculate_change_pct(response.data)

        return PriceSnapshot(
            price=latest.close_buy_price,
            change_pct=change_pct,
            currency="IDR",
            as_of=latest.last_updated_at,
        )

    @staticmethod
    def _calculate_change_pct(entries: list[GoldPriceEntry]) -> float | None:
        """Percent change between the latest and previous day's closing buy price."""
        if len(entries) < 2:
            return None
        latest, previous = entries[-1], entries[-2]
        if not previous.close_buy_price:
            return None
        return (latest.close_buy_price - previous.close_buy_price) / previous.close_buy_price * 100
