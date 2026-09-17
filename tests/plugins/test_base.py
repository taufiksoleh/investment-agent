"""Tests for AssetAnalysisPlugin's generic `get_news()` flow, in particular
its opt-in default: a plugin that doesn't override `build_news_prompt()`
must raise `NewsNotSupportedError` rather than silently doing nothing."""

import pytest

from investment_agent.plugins.base import AssetAnalysisPlugin
from investment_agent.shared.base_models import PriceSnapshot
from investment_agent.shared.exceptions import NewsNotSupportedError


class _BarePlugin(AssetAnalysisPlugin):
    """A plugin implementing only the two required methods - no news support."""

    slug = "bare"
    display_name = "Bare"

    def __init__(self, agent_client, price_snapshot: PriceSnapshot) -> None:
        super().__init__(agent_client)
        self._price_snapshot = price_snapshot

    async def get_current_price(self) -> PriceSnapshot:
        return self._price_snapshot

    def build_prompt(self, price_snapshot: PriceSnapshot) -> str:
        return "prompt"


async def test_get_news_raises_for_plugin_without_news_support(
    fake_agent_client, sample_price_snapshot
) -> None:
    plugin = _BarePlugin(agent_client=fake_agent_client, price_snapshot=sample_price_snapshot)

    with pytest.raises(NewsNotSupportedError):
        await plugin.get_news()
