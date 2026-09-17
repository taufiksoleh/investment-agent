"""Adapter between BMoney's mutual-fund product APIs and the generic
analysis use case.

This is the ONLY place in the mutual fund gateway allowed to know the
products API's URL shape and payload format - `gateway.py` just calls
`fetch_price()`. Backed by BMoney's public mutual-fund product endpoints
(`GET https://api.bmoney.id/_exclusive/bmoney/mutual-fund/products/{id}`
and `.../products/{id}/navs`), addressed by BMoney's own numeric product
id (not the ISIN code - the id is what BMoney's own detail/history
endpoints key on). This adapter always resolves to one specific fund, so
the gateway ends up representing one fund (mirrors gold representing one
specific commodity), configured via `Settings.mutual_fund_product_id`.
"""

from datetime import UTC, datetime

import httpx

from investment_agent.domain.models import PriceSnapshot
from investment_agent.gateways.mutual_fund.models import (
    MutualFundNavEntry,
    MutualFundNavHistoryResponse,
    MutualFundProduct,
    MutualFundProductDetailResponse,
)
from investment_agent.infrastructure.exceptions import UpstreamPriceUnavailableError
from investment_agent.infrastructure.http_client import InternalApiClient


class InternalMutualFundPriceAdapter:
    """Fetches one specific fund's current NAV from BMoney's product APIs.

    `product_id` is BMoney's own internal numeric id for a fund (as used
    in its `/products/{id}` and `/products/{id}/navs` endpoints) - it
    picks which one fund this adapter (and therefore the gateway it
    belongs to) represents.
    """

    def __init__(
        self,
        http_client: InternalApiClient,
        product_id: int,
        endpoint: str = "/_exclusive/bmoney/mutual-fund/products",
    ) -> None:
        self._http_client = http_client
        self._product_id = product_id
        self._endpoint = endpoint
        # Set by fetch_price(), read by MutualFundGateway.build_prompt() for
        # context (fund name/category/manager) that PriceSnapshot doesn't
        # carry. Safe because Analyzable.analyze() always calls
        # get_current_price() immediately before build_prompt(), in that
        # order - a deliberate exception to gold's fully-stateless adapter,
        # not an accidental one.
        self.last_product: MutualFundProduct | None = None

    async def fetch_price(self) -> PriceSnapshot:
        """Fetch the fund's detail + NAV history and normalize into a `PriceSnapshot`.

        Normalizing here (instead of in the gateway) is what lets
        `Analyzable.analyze()` stay asset-agnostic: it only ever deals with
        `PriceSnapshot`, never the raw product/NAV-history shapes.
        """
        try:
            detail_payload = await self._http_client.get_json(
                f"{self._endpoint}/{self._product_id}"
            )
        except httpx.HTTPStatusError as exc:
            raise UpstreamPriceUnavailableError(
                f"Mutual fund product API returned no data for product '{self._product_id}': {exc}"
            ) from exc
        detail = MutualFundProductDetailResponse.model_validate(detail_payload)
        product = detail.data
        self.last_product = product

        navs_payload = await self._http_client.get_json(f"{self._endpoint}/{self._product_id}/navs")
        history = MutualFundNavHistoryResponse.model_validate(navs_payload)
        if not history.data:
            raise UpstreamPriceUnavailableError(
                f"Mutual fund NAV history API returned no data for product '{self._product_id}'."
            )

        return PriceSnapshot(
            price=product.nav.value,
            change_pct=self._calculate_change_pct(history.data),
            currency=product.fund_ccy,
            as_of=datetime.strptime(product.nav.date, "%Y-%m-%d").replace(tzinfo=UTC),
        )

    @staticmethod
    def _calculate_change_pct(entries: list[MutualFundNavEntry]) -> float | None:
        """Percent change between the latest and previous day's NAV.

        Same calculation as `gateways/gold/adapter.py::_calculate_change_pct`,
        but the NAV history endpoint returns entries **newest-first**
        (verified against a live response) - the opposite order from gold's
        bullion price history - so the latest entry is `entries[0]`, not
        `entries[-1]`.
        """
        if len(entries) < 2:
            return None
        latest, previous = entries[0], entries[1]
        if not previous.value:
            return None
        return (latest.value - previous.value) / previous.value * 100
