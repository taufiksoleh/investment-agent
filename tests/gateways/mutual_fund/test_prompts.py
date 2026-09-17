"""Tests for build_mutual_fund_prompt(): verifies the NAV is embedded using
Rupiah formatting (never the raw "IDR" code), fund context is present, and
the JSON output contract is present."""

from investment_agent.gateways.mutual_fund.models import MutualFundProduct
from investment_agent.gateways.mutual_fund.prompts import build_mutual_fund_prompt


def _sample_product() -> MutualFundProduct:
    return MutualFundProduct.model_validate(
        {
            "isin_code": "IDN000000809",
            "fund_name": "Schroder Dana Prestasi Plus",
            "fund_type": "equity",
            "fund_type_text": "Saham",
            "fund_ccy": "IDR",
            "asset_under_management": 2454765225512,
            "risk_profile": "High",
            "nav": {"date": "2026-09-16", "value": 31468.57},
            "return_infos": [{"name": "one_day", "percentage": -0.0068}],
            "investment_manager": {
                "name": "Schroder Investment Management Indonesia",
                "full_name": "PT Schroder Investment Management Indonesia",
            },
        }
    )


def test_prompt_formats_nav_as_rupiah_not_idr_code(sample_price_snapshot) -> None:
    prompt = build_mutual_fund_prompt(sample_price_snapshot, _sample_product())

    assert "Rp1.985.000" in prompt
    assert "NAV di atas adalah satu-satunya angka yang sah" in prompt


def test_prompt_includes_fund_context(sample_price_snapshot) -> None:
    prompt = build_mutual_fund_prompt(sample_price_snapshot, _sample_product())

    assert "Schroder Dana Prestasi Plus" in prompt
    assert "PT Schroder Investment Management Indonesia" in prompt
    assert "Saham" in prompt


def test_prompt_requests_the_expected_json_keys(sample_price_snapshot) -> None:
    prompt = build_mutual_fund_prompt(sample_price_snapshot, _sample_product())

    for key in (
        "key_drivers",
        "technical_summary",
        "fundamental_summary",
        "recommendation",
        "confidence_level",
        "risk_scenario",
    ):
        assert f'"{key}"' in prompt
