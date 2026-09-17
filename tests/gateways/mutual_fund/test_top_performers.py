"""Tests for fetch_top_performing_funds(): verifies BMoney's curated
top-performers payload (a trimmed real excerpt) is parsed as plain data,
with no LLM/Analyzable involvement."""

import respx
from httpx import Response

from investment_agent.gateways.mutual_fund.top_performers import fetch_top_performing_funds
from investment_agent.infrastructure.http_client import InternalApiClient

TOP_PERFORMANCES_RESPONSE = {
    "data": {
        "title": (
            "Berdasarkan riwayat kinerja produk dalam 1 tahun terakhir dan bukan "
            "prediksi kinerja produk di masa depan."
        ),
        "products": [
            {
                "id": 115,
                "fund_name": "Henan Ultima Money Market",
                "fund_type_text": "Pasar Uang",
                "nav": {"date": "2026-09-16", "value": 1761.5239},
                "return_value": 0.0546,
                "tags": [],
            },
            {
                "id": 62,
                "fund_name": "Bahana Likuid Syariah Kelas G",
                "fund_type_text": "Pasar Uang",
                "nav": {"date": "2026-09-16", "value": 1308.7},
                "return_value": 0.0473,
                "tags": ["sharia"],
            },
        ],
    },
    "meta": {"offset": 0, "limit": 300, "total": 2, "http_status": 200},
}


@respx.mock
async def test_fetch_top_performing_funds_parses_curated_list() -> None:
    respx.get(
        "http://internal-api.test/_exclusive/bmoney/mutual-fund/products/top-performances"
    ).mock(return_value=Response(200, json=TOP_PERFORMANCES_RESPONSE))
    http_client = InternalApiClient(base_url="http://internal-api.test")

    result = await fetch_top_performing_funds(http_client)

    assert len(result.data.products) == 2
    assert result.data.products[0].fund_name == "Henan Ultima Money Market"
    assert result.data.products[0].return_value == 0.0546
    assert result.data.products[1].tags == ["sharia"]
