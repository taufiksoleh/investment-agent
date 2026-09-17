"""Mutual-fund-specific data shapes.

Mirrors BMoney's public mutual-fund API payloads - the products list
(`GET .../products`), a single product's detail (`GET .../products/{id}`),
its NAV history (`GET .../products/{id}/navs`), and the curated
top-performers list (`GET .../products/top-performances`) - so a change in
any of those APIs only touches this file. Only the fields this app
actually uses are declared - the upstream responses have many more (fees,
prospectus URLs, asset allocation breakdowns, etc.) that pydantic silently
ignores.

Unlike gold (one global commodity), these endpoints list many distinct
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


class MutualFundProductDetailResponse(BaseModel):
    """Envelope returned by `GET /_exclusive/bmoney/mutual-fund/products/{id}`.

    Same `MutualFundProduct` shape as a list item, just wrapped as one
    object under `data` instead of a list.
    """

    data: MutualFundProduct


class MutualFundNavEntry(BaseModel):
    """One day's NAV history point."""

    date: str
    value: float


class MutualFundNavHistoryResponse(BaseModel):
    """Envelope returned by `GET /_exclusive/bmoney/mutual-fund/products/{id}/navs`."""

    data: list[MutualFundNavEntry]


class TopPerformerEntry(BaseModel):
    """One fund's entry in BMoney's curated top-performers list."""

    id: int
    fund_name: str
    fund_type_text: str
    nav: MutualFundNav
    return_value: float
    tags: list[str]


class TopPerformersData(BaseModel):
    """The curated list itself, plus BMoney's own disclaimer title."""

    title: str
    products: list[TopPerformerEntry]


class TopPerformersResponse(BaseModel):
    """Envelope returned by `GET /_exclusive/bmoney/mutual-fund/products/top-performances`."""

    data: TopPerformersData


class MutualFundAnalysis(AssetAnalysis):
    """Mutual fund's analysis output. Identical to the base schema for now -
    this is the extension point for mutual-fund-only fields added later."""
