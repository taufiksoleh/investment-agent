"""Mutual-fund-specific routes.

`api/router.py` is deliberately generic ("intentionally no per-asset-class
route"). Mutual fund needs two routes that don't fit that generic shape,
so they live here instead of contradicting that file's stated contract:

- `GET /analyze/mutual-fund/{product_id}` - unlike every other gateway,
  which is resolved from the registry built once at startup, this route
  needs a `MutualFundGateway` parameterized by the product id in the URL -
  the registry pattern only supports one fixed gateway per slug, which
  doesn't fit "analyze any of ~40 funds by id." `get_mutual_fund_gateway()`
  below builds one per request via `MutualFundGateway.for_product()` (the
  same factory `main.py` uses for the default gateway), reusing the
  app-wide `agent_client`/`internal_api_client` from `app.state` rather
  than opening new HTTP connections per request. It's wired in as a
  `Depends()`, the same idiom `api/router.py`'s `get_registry()` uses -
  the only difference is this one calls a factory instead of doing a
  registry lookup.
- `GET /mutual-funds/top-performers` - a plain data list from BMoney's own
  curated ranking, no LLM reasoning involved, so it doesn't go through
  `Analyzable` at all.
"""

from fastapi import APIRouter, Depends, Request

from investment_agent.domain.models import AssetAnalysis
from investment_agent.gateways.mutual_fund.gateway import MutualFundGateway
from investment_agent.gateways.mutual_fund.models import TopPerformersResponse
from investment_agent.gateways.mutual_fund.top_performers import fetch_top_performing_funds

router = APIRouter()


def get_mutual_fund_gateway(product_id: int, request: Request) -> MutualFundGateway:
    """Build a `MutualFundGateway` for `product_id`, sharing the app-wide infra clients."""
    return MutualFundGateway.for_product(
        product_id, request.app.state.agent_client, request.app.state.internal_api_client
    )


@router.get("/analyze/mutual-fund/{product_id}", response_model=AssetAnalysis)
async def analyze_mutual_fund_product(
    gateway: MutualFundGateway = Depends(get_mutual_fund_gateway),
) -> AssetAnalysis:
    """Run analysis for one specific mutual fund, by BMoney's numeric product id.

    Raises a 502 (via `UpstreamPriceUnavailableError`'s exception handler)
    when `product_id` doesn't exist upstream.
    """
    return await gateway.analyze()


@router.get("/mutual-funds/top-performers", response_model=TopPerformersResponse)
async def get_top_performing_mutual_funds(request: Request) -> TopPerformersResponse:
    """Return BMoney's own curated top-performing mutual funds list.

    Plain data, not an `Analyzable` flow - there's nothing for an LLM to
    reason about here, just BMoney's ranking reshaped.
    """
    return await fetch_top_performing_funds(request.app.state.internal_api_client)
