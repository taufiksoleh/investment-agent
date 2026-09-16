"""Tests for InternalGoldPriceAdapter: verifies the internal API payload is
normalized into a generic PriceSnapshot correctly."""

import respx
from httpx import Response

from investment_agent.plugins.gold.adapters import InternalGoldPriceAdapter
from investment_agent.shared.http_client import InternalApiClient


@respx.mock
async def test_fetch_price_normalizes_internal_payload() -> None:
    respx.get("http://internal-api.test/prices/gold").mock(
        return_value=Response(
            200,
            json={
                "price_idr_per_gram": 1_985_000.0,
                "change_pct_24h": -0.8,
                "as_of": "2026-01-01T00:00:00Z",
            },
        )
    )
    http_client = InternalApiClient(base_url="http://internal-api.test")
    adapter = InternalGoldPriceAdapter(http_client)

    snapshot = await adapter.fetch_price()

    assert snapshot.price == 1_985_000.0
    assert snapshot.change_pct == -0.8
    assert snapshot.currency == "IDR"
