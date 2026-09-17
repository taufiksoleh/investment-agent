"""Tests for mutual-fund-specific routes, exercised through the real app
with the outbound BMoney calls mocked (real trimmed excerpts) and the
agent client patched to avoid invoking the actual Claude Agent SDK."""

import json

import respx
from fastapi.testclient import TestClient
from httpx import Response

from investment_agent.infrastructure.agent_client import ClaudeAgentClient
from investment_agent.main import app

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
    }
}
NAV_HISTORY_RESPONSE = {
    "data": [
        {"date": "2026-09-16", "value": 1761.5239},
        {"date": "2026-09-15", "value": 1761.194},
    ]
}
TOP_PERFORMANCES_RESPONSE = {
    "data": {
        "title": "Berdasarkan riwayat kinerja produk dalam 1 tahun terakhir.",
        "products": [
            {
                "id": 115,
                "fund_name": "Henan Ultima Money Market",
                "fund_type_text": "Pasar Uang",
                "nav": {"date": "2026-09-16", "value": 1761.5239},
                "return_value": 0.0546,
                "tags": [],
            }
        ],
    }
}


async def _fake_run_analysis(self, prompt: str) -> str:
    return json.dumps(
        {
            "key_drivers": ["test driver"],
            "technical_summary": "test technical",
            "fundamental_summary": "test fundamental",
            "recommendation": "NEUTRAL",
            "confidence_level": 0.5,
            "risk_scenario": "test risk",
        }
    )


@respx.mock
def test_analyze_specific_mutual_fund_product(monkeypatch) -> None:
    monkeypatch.setattr(ClaudeAgentClient, "run_analysis", _fake_run_analysis)
    respx.get("https://api.bmoney.id/_exclusive/bmoney/mutual-fund/products/115").mock(
        return_value=Response(200, json=PRODUCT_DETAIL_RESPONSE)
    )
    respx.get("https://api.bmoney.id/_exclusive/bmoney/mutual-fund/products/115/navs").mock(
        return_value=Response(200, json=NAV_HISTORY_RESPONSE)
    )

    with TestClient(app) as client:
        response = client.get("/analyze/mutual-fund/115")

    assert response.status_code == 200
    body = response.json()
    assert body["current_price"] == 1761.5239
    assert body["recommendation"] == "NEUTRAL"


@respx.mock
def test_analyze_unknown_product_returns_502(monkeypatch) -> None:
    monkeypatch.setattr(ClaudeAgentClient, "run_analysis", _fake_run_analysis)
    respx.get("https://api.bmoney.id/_exclusive/bmoney/mutual-fund/products/999999").mock(
        return_value=Response(404, json={"detail": "not found"})
    )

    with TestClient(app) as client:
        response = client.get("/analyze/mutual-fund/999999")

    assert response.status_code == 502


@respx.mock
def test_top_performers_endpoint_returns_curated_list() -> None:
    respx.get(
        "https://api.bmoney.id/_exclusive/bmoney/mutual-fund/products/top-performances"
    ).mock(return_value=Response(200, json=TOP_PERFORMANCES_RESPONSE))

    with TestClient(app) as client:
        response = client.get("/mutual-funds/top-performers")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["products"][0]["fund_name"] == "Henan Ultima Money Market"
