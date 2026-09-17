"""Tests for InternalMutualFundPriceAdapter: verifies BMoney's per-product
detail + NAV history payloads (trimmed real excerpts) are normalized into
a generic PriceSnapshot correctly, keyed by BMoney's numeric product id."""

import pytest
import respx
from httpx import Response

from investment_agent.gateways.mutual_fund.adapter import InternalMutualFundPriceAdapter
from investment_agent.infrastructure.exceptions import UpstreamPriceUnavailableError
from investment_agent.infrastructure.http_client import InternalApiClient

PRODUCT_DETAIL_RESPONSE = {
    "data": {
        "isin_code": "IDN000209103",
        "fund_name": "Henan Ultima Money Market",
        "fund_type": "money_market",
        "fund_type_text": "Pasar Uang",
        "fund_ccy": "IDR",
        "asset_under_management": 1370313447824,
        "risk_profile": "Low",
        "nav": {"date": "2026-09-16", "value": 1761.5239},
        "return_infos": [{"name": "one_day", "percentage": 0.0002}],
        "investment_manager": {
            "name": "Henan Putihrai Asset Management",
            "full_name": "PT Henan Putihrai Asset Management",
        },
    },
    "meta": {"http_status": 200},
}

# BMoney returns NAV history newest-first (verified against a live response) -
# the opposite order from gold's bullion price history.
NAV_HISTORY_RESPONSE = {
    "data": [
        {"date": "2026-09-16", "value": 1761.5239},
        {"date": "2026-09-15", "value": 1761.194},
        {"date": "2026-09-14", "value": 1760.9094},
    ],
    "meta": {"http_status": 200},
}


@respx.mock
async def test_fetch_price_normalizes_product_and_computes_change_from_history() -> None:
    respx.get("http://internal-api.test/_exclusive/bmoney/mutual-fund/products/115").mock(
        return_value=Response(200, json=PRODUCT_DETAIL_RESPONSE)
    )
    respx.get("http://internal-api.test/_exclusive/bmoney/mutual-fund/products/115/navs").mock(
        return_value=Response(200, json=NAV_HISTORY_RESPONSE)
    )
    http_client = InternalApiClient(base_url="http://internal-api.test")
    adapter = InternalMutualFundPriceAdapter(http_client, product_id=115)

    snapshot = await adapter.fetch_price()

    assert snapshot.price == 1761.5239
    assert snapshot.currency == "IDR"
    assert snapshot.change_pct == pytest.approx((1761.5239 - 1761.194) / 1761.194 * 100)
    assert adapter.last_product is not None
    assert adapter.last_product.fund_name == "Henan Ultima Money Market"


@respx.mock
async def test_fetch_price_with_single_history_entry_has_no_change_pct() -> None:
    respx.get("http://internal-api.test/_exclusive/bmoney/mutual-fund/products/115").mock(
        return_value=Response(200, json=PRODUCT_DETAIL_RESPONSE)
    )
    respx.get("http://internal-api.test/_exclusive/bmoney/mutual-fund/products/115/navs").mock(
        return_value=Response(200, json={"data": [NAV_HISTORY_RESPONSE["data"][0]]})
    )
    http_client = InternalApiClient(base_url="http://internal-api.test")
    adapter = InternalMutualFundPriceAdapter(http_client, product_id=115)

    snapshot = await adapter.fetch_price()

    assert snapshot.change_pct is None


@respx.mock
async def test_fetch_price_raises_when_history_is_empty() -> None:
    respx.get("http://internal-api.test/_exclusive/bmoney/mutual-fund/products/115").mock(
        return_value=Response(200, json=PRODUCT_DETAIL_RESPONSE)
    )
    respx.get("http://internal-api.test/_exclusive/bmoney/mutual-fund/products/115/navs").mock(
        return_value=Response(200, json={"data": []})
    )
    http_client = InternalApiClient(base_url="http://internal-api.test")
    adapter = InternalMutualFundPriceAdapter(http_client, product_id=115)

    with pytest.raises(UpstreamPriceUnavailableError):
        await adapter.fetch_price()


@respx.mock
async def test_fetch_price_raises_upstream_error_for_unknown_product() -> None:
    # Detail and NAV history are fetched concurrently, so both must be
    # mocked even though only the detail call is expected to fail here.
    respx.get("http://internal-api.test/_exclusive/bmoney/mutual-fund/products/999999").mock(
        return_value=Response(404, json={"detail": "not found"})
    )
    respx.get("http://internal-api.test/_exclusive/bmoney/mutual-fund/products/999999/navs").mock(
        return_value=Response(404, json={"detail": "not found"})
    )
    http_client = InternalApiClient(base_url="http://internal-api.test")
    adapter = InternalMutualFundPriceAdapter(http_client, product_id=999999)

    with pytest.raises(UpstreamPriceUnavailableError):
        await adapter.fetch_price()


@respx.mock
async def test_fetch_price_raises_upstream_error_when_navs_endpoint_fails() -> None:
    respx.get("http://internal-api.test/_exclusive/bmoney/mutual-fund/products/115").mock(
        return_value=Response(200, json=PRODUCT_DETAIL_RESPONSE)
    )
    respx.get("http://internal-api.test/_exclusive/bmoney/mutual-fund/products/115/navs").mock(
        return_value=Response(503, json={"detail": "service unavailable"})
    )
    http_client = InternalApiClient(base_url="http://internal-api.test")
    adapter = InternalMutualFundPriceAdapter(http_client, product_id=115)

    with pytest.raises(UpstreamPriceUnavailableError):
        await adapter.fetch_price()
