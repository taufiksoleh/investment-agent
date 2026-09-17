"""Adapter between BMoney's mutual-fund products API and the generic
analysis use case.

This is the ONLY place in the mutual fund gateway allowed to know the
products API's URL shape and payload format - `gateway.py` just calls
`fetch_price()`. Backed by BMoney's public mutual-fund products API
(`GET https://api.bmoney.id/_exclusive/bmoney/mutual-fund/products`),
which lists ~40 funds in one response; this adapter is configured with a
single ISIN code and always resolves to that one fund's data, so the
gateway ends up representing one specific fund (mirrors gold representing
one specific commodity), configured via `Settings.mutual_fund_isin_code`.
"""

from datetime import UTC, datetime

from investment_agent.domain.models import PriceSnapshot
from investment_agent.gateways.mutual_fund.models import (
    MutualFundProduct,
    MutualFundProductsResponse,
)
from investment_agent.infrastructure.exceptions import UpstreamPriceUnavailableError
from investment_agent.infrastructure.http_client import InternalApiClient


class InternalMutualFundPriceAdapter:
    """Fetches one specific fund's current NAV from BMoney's products API.

    The products endpoint returns every fund BMoney lists (money market,
    fixed income, equity, mixed asset); `isin_code` picks which one this
    adapter (and therefore the gateway it belongs to) represents.
    """

    def __init__(
        self,
        http_client: InternalApiClient,
        isin_code: str,
        endpoint: str = "/_exclusive/bmoney/mutual-fund/products",
    ) -> None:
        self._http_client = http_client
        self._isin_code = isin_code
        self._endpoint = endpoint
        # Set by fetch_price(), read by MutualFundGateway.build_prompt() for
        # context (fund name/category/manager) that PriceSnapshot doesn't
        # carry. Safe because Analyzable.analyze() always calls
        # get_current_price() immediately before build_prompt(), in that
        # order - a deliberate exception to gold's fully-stateless adapter,
        # not an accidental one.
        self.last_product: MutualFundProduct | None = None

    async def fetch_price(self) -> PriceSnapshot:
        """Fetch the products list and normalize the configured fund's NAV
        into a `PriceSnapshot`.

        Normalizing here (instead of in the gateway) is what lets
        `Analyzable.analyze()` stay asset-agnostic: it only ever deals with
        `PriceSnapshot`, never the raw products-list shape.
        """
        payload = await self._http_client.get_json(self._endpoint)
        response = MutualFundProductsResponse.model_validate(payload)

        product = next((p for p in response.data if p.isin_code == self._isin_code), None)
        if product is None:
            raise UpstreamPriceUnavailableError(
                f"Mutual fund products API response did not include ISIN "
                f"'{self._isin_code}'."
            )

        self.last_product = product
        return PriceSnapshot(
            price=product.nav.value,
            change_pct=self._one_day_change_pct(product),
            currency=product.fund_ccy,
            as_of=datetime.strptime(product.nav.date, "%Y-%m-%d").replace(tzinfo=UTC),
        )

    @staticmethod
    def _one_day_change_pct(product: MutualFundProduct) -> float | None:
        """The fund's same-day return, converted from a fraction (e.g. 0.0002)
        to a percentage point (0.02) to match gold's `change_pct` convention."""
        one_day = next((r for r in product.return_infos if r.name == "one_day"), None)
        if one_day is None:
            return None
        return one_day.percentage * 100
