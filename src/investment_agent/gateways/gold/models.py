"""Gold-specific data shapes.

`GoldPriceEntry`/`BullionPriceResponse` mirror BMoney's public bullion price
API payload exactly (`GET /bullion/prices?period=...`), so a change in that
API only touches this file. `GoldAnalysis` extends the shared `AssetAnalysis`
as the place to add gold-only output fields later, without affecting the
base schema other gateways rely on.
"""

from datetime import datetime

from pydantic import BaseModel

from investment_agent.domain.models import AssetAnalysis


class GoldPriceEntry(BaseModel):
    """One day's OHLC bullion price record, in IDR per gram.

    Only the fields this app actually uses are declared - the upstream
    response has more (installment prices, markup values, etc.) that
    pydantic silently ignores.
    """

    date: str
    last_updated_at: datetime
    close_buy_price: float


class BullionPriceResponse(BaseModel):
    """Envelope returned by `GET /bullion/prices`."""

    data: list[GoldPriceEntry]


class GoldAnalysis(AssetAnalysis):
    """Gold's analysis output. Identical to the base schema for now - this is
    the extension point for gold-only fields (e.g. spot/futures spread) added later."""
