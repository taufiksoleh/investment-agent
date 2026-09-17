"""Shared test fixtures: fakes for the two external dependencies every
plugin is injected with, so tests never hit a real internal API or the
Claude Agent SDK."""

import json
from datetime import UTC, datetime

import pytest

from investment_agent.domain.models import PriceSnapshot


class FakeAgentClient:
    """Stand-in for `ClaudeAgentClient` that returns a canned JSON response."""

    def __init__(self, response: dict | None = None) -> None:
        self.response = response or {
            "key_drivers": ["placeholder driver"],
            "technical_summary": "placeholder technical summary",
            "fundamental_summary": "placeholder fundamental summary",
            "recommendation": "NEUTRAL",
            "confidence_level": 0.5,
            "risk_scenario": "placeholder risk scenario",
        }
        self.received_prompts: list[str] = []

    async def run_analysis(self, prompt: str) -> str:
        self.received_prompts.append(prompt)
        return json.dumps(self.response)


@pytest.fixture
def fake_agent_client() -> FakeAgentClient:
    return FakeAgentClient()


@pytest.fixture
def sample_price_snapshot() -> PriceSnapshot:
    return PriceSnapshot(
        price=1_985_000.0,
        change_pct=1.2,
        currency="IDR",
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
    )
