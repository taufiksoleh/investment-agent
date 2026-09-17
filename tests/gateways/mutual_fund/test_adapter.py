"""Tests for InternalMutualFundPriceAdapter: verifies BMoney's mutual-fund
products payload (a trimmed real excerpt) is normalized into a generic
PriceSnapshot correctly, keyed by ISIN code."""

import pytest
import respx
from httpx import Response

from investment_agent.gateways.mutual_fund.adapter import InternalMutualFundPriceAdapter
from investment_agent.infrastructure.exceptions import UpstreamPriceUnavailableError
from investment_agent.infrastructure.http_client import InternalApiClient

SAMPLE_PRODUCTS_RESPONSE = {
    "data": [
        {
            "isin_code": "IDN000000809",
            "fund_name": "Schroder Dana Prestasi Plus",
            "fund_type": "equity",
            "fund_type_text": "Saham",
            "fund_ccy": "IDR",
            "asset_under_management": 2454765225512,
            "risk_profile": "High",
            "nav": {"date": "2026-09-16", "value": 31468.57},
            "return_infos": [
                {"name": "one_day", "percentage": -0.0068},
                {"name": "one_year", "percentage": -0.0201},
            ],
            "investment_manager": {
                "name": "Schroder Investment Management Indonesia",
                "full_name": "PT Schroder Investment Management Indonesia",
            },
        },
        {
            "isin_code": "IDN000209103",
            "fund_name": "Henan Ultima Money Market",
            "fund_type": "money_market",
            "fund_type_text": "Pasar Uang",
            "fund_ccy": "IDR",
            "asset_under_management": 1370313447824,
            "risk_profile": "Low",
            "nav": {"date": "2026-09-16", "value": 1761.5239},
            "return_infos": [
                {"name": "one_day", "percentage": 0.0002},
            ],
            "investment_manager": {
                "name": "Henan Putihrai Asset Management",
                "full_name": "PT Henan Putihrai Asset Management",
            },
        },
    ],
    "meta": {"offset": 0, "limit": 40, "total": 2, "http_status": 200},
}


@respx.mock
async def test_fetch_price_normalizes_matched_fund() -> None:
    respx.get("http://internal-api.test/_exclusive/bmoney/mutual-fund/products").mock(
        return_value=Response(200, json=SAMPLE_PRODUCTS_RESPONSE)
    )
    http_client = InternalApiClient(base_url="http://internal-api.test")
    adapter = InternalMutualFundPriceAdapter(http_client, isin_code="IDN000000809")

    snapshot = await adapter.fetch_price()

    assert snapshot.price == 31468.57
    assert snapshot.currency == "IDR"
    assert snapshot.change_pct == pytest.approx(-0.68)
    assert adapter.last_product is not None
    assert adapter.last_product.fund_name == "Schroder Dana Prestasi Plus"


@respx.mock
async def test_fetch_price_selects_correct_fund_by_isin() -> None:
    respx.get("http://internal-api.test/_exclusive/bmoney/mutual-fund/products").mock(
        return_value=Response(200, json=SAMPLE_PRODUCTS_RESPONSE)
    )
    http_client = InternalApiClient(base_url="http://internal-api.test")
    adapter = InternalMutualFundPriceAdapter(http_client, isin_code="IDN000209103")

    snapshot = await adapter.fetch_price()

    assert snapshot.price == 1761.5239
    assert snapshot.change_pct == pytest.approx(0.02)
    assert adapter.last_product.fund_name == "Henan Ultima Money Market"


@respx.mock
async def test_fetch_price_raises_when_isin_not_in_response() -> None:
    respx.get("http://internal-api.test/_exclusive/bmoney/mutual-fund/products").mock(
        return_value=Response(200, json=SAMPLE_PRODUCTS_RESPONSE)
    )
    http_client = InternalApiClient(base_url="http://internal-api.test")
    adapter = InternalMutualFundPriceAdapter(http_client, isin_code="NONEXISTENT")

    with pytest.raises(UpstreamPriceUnavailableError):
        await adapter.fetch_price()
