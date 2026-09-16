"""Gold-specific data shapes.

`GoldPrice` mirrors the internal price API's payload exactly, so a change in
that API only touches this file. `GoldAnalysis` extends the shared
`AssetAnalysis` as the place to add gold-only output fields later, without
affecting the base schema other plugins rely on.
"""

from datetime import datetime

from pydantic import BaseModel

from investment_agent.shared.base_models import AssetAnalysis


class GoldPrice(BaseModel):
    """Raw response shape from the internal gold price endpoint."""

    price_usd_per_ounce: float
    change_pct_24h: float | None = None
    as_of: datetime


class GoldAnalysis(AssetAnalysis):
    """Gold's analysis output. Identical to the base schema for now - this is
    the extension point for gold-only fields (e.g. spot/futures spread) added later."""
