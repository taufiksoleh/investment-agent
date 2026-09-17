"""Tests for GoldAnalysisPlugin, exercising the generic `analyze()` flow
defined in AssetAnalysisPlugin with fake price/agent dependencies injected."""

from unittest.mock import AsyncMock

from investment_agent.plugins.gold.plugin import GoldAnalysisPlugin
from investment_agent.shared.base_models import Recommendation


async def test_analyze_merges_price_snapshot_and_agent_reasoning(
    fake_agent_client, sample_price_snapshot
) -> None:
    price_adapter = AsyncMock()
    price_adapter.fetch_price.return_value = sample_price_snapshot

    plugin = GoldAnalysisPlugin(agent_client=fake_agent_client, price_adapter=price_adapter)

    result = await plugin.analyze()

    assert result.current_price == sample_price_snapshot.price
    assert result.price_change_pct == sample_price_snapshot.change_pct
    assert result.recommendation == Recommendation.NEUTRAL
    assert fake_agent_client.received_prompts, "plugin must send a prompt to the agent client"
