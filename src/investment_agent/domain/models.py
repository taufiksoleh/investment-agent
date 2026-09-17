"""Entities shared by the core app and every gateway/use case.

Nothing asset-specific belongs here. Any field a single asset class needs but
others don't (e.g. a gold-only "spot vs futures spread") belongs in that
gateway's own `models.py`, as a subclass of `AssetAnalysis`.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Recommendation(StrEnum):
    """The three actions an analysis can conclude with."""

    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


class PriceSnapshot(BaseModel):
    """A verified point-in-time price, always sourced from an internal adapter.

    This is the hand-off point between "real data" and "reasoning": the
    `Analyzable` use case only ever gets price numbers from this model, never
    from the Claude Agent SDK.
    """

    price: float
    change_pct: float | None = None
    currency: str = "IDR"
    as_of: datetime


class AssetAnalysis(BaseModel):
    """Common analysis output every asset gateway must return.

    The API response shape is identical across asset types on purpose - it's
    what lets `/analyze/{asset_type}` stay a single generic endpoint instead
    of one per asset class.
    """

    current_price: float
    price_change_pct: float | None = None
    key_drivers: list[str] = Field(default_factory=list)
    technical_summary: str
    fundamental_summary: str
    recommendation: Recommendation
    confidence_level: float = Field(ge=0, le=1)
    risk_scenario: str
