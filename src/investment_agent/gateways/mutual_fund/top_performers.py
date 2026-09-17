"""Fetches BMoney's curated top-performing mutual funds list.

This is BMoney-shape-specific parsing, same as `adapter.py`, so it lives
in the gateway layer - not in `use_cases/`, which stays asset-agnostic.
Unlike `adapter.py`, this isn't feeding the `Analyzable` flow: it's a
plain data list with nothing for an LLM to reason about, so there's no
`PriceSnapshot`/`AssetAnalysis` involved here at all.
"""

from investment_agent.gateways.mutual_fund.models import TopPerformersResponse
from investment_agent.infrastructure.http_client import InternalApiClient

_ENDPOINT = "/_exclusive/bmoney/mutual-fund/products/top-performances"


async def fetch_top_performing_funds(http_client: InternalApiClient) -> TopPerformersResponse:
    """Fetch and validate BMoney's curated top-performers list, as-is.

    No period parameter is exposed here because BMoney's response doesn't
    expose one either (observed fixed to a 1-year-return ranking) - this
    doesn't invent a filter the upstream API doesn't support.
    """
    payload = await http_client.get_json(_ENDPOINT)
    return TopPerformersResponse.model_validate(payload)
