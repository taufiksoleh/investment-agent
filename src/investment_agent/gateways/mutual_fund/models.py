"""Mutual-fund-specific data shapes.

`MutualFundProduct`/`MutualFundProductsResponse` mirror BMoney's public
mutual-fund products API payload
(`GET /_exclusive/bmoney/mutual-fund/products`), so a change in that API
only touches this file. Only the fields this app actually uses are
declared - the upstream response has many more (fees, prospectus URLs,
asset allocation breakdowns, etc.) that pydantic silently ignores.

Unlike gold (one global commodity), this endpoint lists many distinct
funds; `MutualFundAnalysis` is the extension point for mutual-fund-only
output fields added later, without affecting the base schema other
gateways rely on.
"""

from pydantic import BaseModel

from investment_agent.domain.models import AssetAnalysis


class MutualFundReturnInfo(BaseModel):
    """One period's return figure (e.g. "one_day", "one_year") for a fund."""

    name: str
    percentage: float


class MutualFundNav(BaseModel):
    """A fund's Net Asset Value per unit as of a given date."""

    date: str
    value: float


class InvestmentManager(BaseModel):
    """The asset management company managing a fund."""

    name: str
    full_name: str


class MutualFundProduct(BaseModel):
    """One fund entry from BMoney's mutual-fund products list."""

    isin_code: str
    fund_name: str
    fund_type: str
    fund_type_text: str
    fund_ccy: str
    asset_under_management: float
    risk_profile: str
    nav: MutualFundNav
    return_infos: list[MutualFundReturnInfo]
    investment_manager: InvestmentManager


class MutualFundProductsResponse(BaseModel):
    """Envelope returned by `GET /_exclusive/bmoney/mutual-fund/products`."""

    data: list[MutualFundProduct]


class MutualFundAnalysis(AssetAnalysis):
    """Mutual fund's analysis output. Identical to the base schema for now -
    this is the extension point for mutual-fund-only fields added later."""
