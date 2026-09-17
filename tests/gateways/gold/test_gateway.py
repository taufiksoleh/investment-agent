"""Tests for GoldGateway, exercising the generic `analyze()` flow defined in
the `Analyzable` use case with fake price/agent dependencies injected."""

from unittest.mock import AsyncMock

from investment_agent.domain.models import Recommendation
from investment_agent.gateways.gold.gateway import GoldGateway


async def test_analyze_merges_price_snapshot_and_agent_reasoning(
    fake_agent_client, sample_price_snapshot
) -> None:
    price_adapter = AsyncMock()
    price_adapter.fetch_price.return_value = sample_price_snapshot

    gateway = GoldGateway(agent_client=fake_agent_client, price_adapter=price_adapter)

    result = await gateway.analyze()

    assert result.current_price == sample_price_snapshot.price
    assert result.price_change_pct == sample_price_snapshot.change_pct
    assert result.recommendation == Recommendation.NEUTRAL
    assert fake_agent_client.received_prompts, "gateway must send a prompt to the agent client"
