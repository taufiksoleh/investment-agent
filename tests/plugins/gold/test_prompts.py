"""Tests for build_gold_prompt(): verifies the price is embedded using Rupiah
formatting (never the raw "IDR" code) and the JSON output contract is present."""

from investment_agent.plugins.gold.prompts import build_gold_prompt


def test_prompt_formats_price_as_rupiah_not_idr_code(sample_price_snapshot) -> None:
    prompt = build_gold_prompt(sample_price_snapshot)

    assert "Rp1.985.000" in prompt
    assert "harga di atas adalah satu-satunya angka yang sah" in prompt


def test_prompt_requests_the_expected_json_keys(sample_price_snapshot) -> None:
    prompt = build_gold_prompt(sample_price_snapshot)

    for key in (
        "key_drivers",
        "technical_summary",
        "fundamental_summary",
        "recommendation",
        "confidence_level",
        "risk_scenario",
    ):
        assert f'"{key}"' in prompt
