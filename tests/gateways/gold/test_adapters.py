"""Tests for InternalGoldPriceAdapter: verifies BMoney's bullion price API
payload is normalized into a generic PriceSnapshot correctly."""

import pytest
import respx
from httpx import Response

from investment_agent.gateways.gold.adapters import InternalGoldPriceAdapter
from investment_agent.infrastructure.exceptions import UpstreamPriceUnavailableError
from investment_agent.infrastructure.http_client import InternalApiClient

BULLION_PRICES_RESPONSE = {
    "data": [
        {
            "date": "2026-09-15",
            "last_updated_at": "2026-09-15T23:46:40.000+07:00",
            "close_buy_price": 2492090.0,
        },
        {
            "date": "2026-09-16",
            "last_updated_at": "2026-09-16T15:02:02.000+07:00",
            "close_buy_price": 2505712.0,
        },
    ],
    "meta": {"http_status": 200},
}


@respx.mock
async def test_fetch_price_normalizes_latest_entry_and_change_pct() -> None:
    respx.get("http://internal-api.test/bullion/prices").mock(
        return_value=Response(200, json=BULLION_PRICES_RESPONSE)
    )
    http_client = InternalApiClient(base_url="http://internal-api.test")
    adapter = InternalGoldPriceAdapter(http_client)

    snapshot = await adapter.fetch_price()

    assert snapshot.price == 2505712.0
    assert snapshot.change_pct == pytest.approx((2505712.0 - 2492090.0) / 2492090.0 * 100)
    assert snapshot.currency == "IDR"


@respx.mock
async def test_fetch_price_with_single_entry_has_no_change_pct() -> None:
    respx.get("http://internal-api.test/bullion/prices").mock(
        return_value=Response(200, json={"data": [BULLION_PRICES_RESPONSE["data"][-1]]})
    )
    http_client = InternalApiClient(base_url="http://internal-api.test")
    adapter = InternalGoldPriceAdapter(http_client)

    snapshot = await adapter.fetch_price()

    assert snapshot.change_pct is None


@respx.mock
async def test_fetch_price_raises_when_upstream_has_no_data() -> None:
    respx.get("http://internal-api.test/bullion/prices").mock(
        return_value=Response(200, json={"data": []})
    )
    http_client = InternalApiClient(base_url="http://internal-api.test")
    adapter = InternalGoldPriceAdapter(http_client)

    with pytest.raises(UpstreamPriceUnavailableError):
        await adapter.fetch_price()
