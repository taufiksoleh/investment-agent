"""Tests for GoldAnalysisPlugin, exercising the generic `analyze()`/`get_news()`
flows defined in AssetAnalysisPlugin with fake price/agent dependencies injected."""

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


async def test_get_news_returns_items_tagged_with_slug(
    fake_agent_client, sample_price_snapshot
) -> None:
    fake_agent_client.response = {
        "items": [
            {
                "title": "The Fed menahan suku bunga",
                "summary": "Menahan daya tarik emas sebagai aset non-yield.",
                "source": "Reuters",
                "published_at": "2026-01-04",
            }
        ]
    }
    price_adapter = AsyncMock()
    price_adapter.fetch_price.return_value = sample_price_snapshot

    plugin = GoldAnalysisPlugin(agent_client=fake_agent_client, price_adapter=price_adapter)

    news = await plugin.get_news()

    assert news.slug == "gold"
    assert len(news.items) == 1
    assert news.items[0].title == "The Fed menahan suku bunga"
    assert fake_agent_client.received_prompts, "plugin must send a news prompt to the agent client"
