"""Contract tests every registered gateway must satisfy identically,
regardless of which asset it represents.

Each gateway's own test file (`gateways/gold/test_gateway.py`,
`gateways/mutual_fund/test_gateway.py`) already exercises its `analyze()`
flow in isolation. This file guards the thing those can't: that every
gateway conforms to the shared `Analyzable` contract the same way, so a
future gateway can't quietly drift (e.g. return a `confidence_level`
outside 0-1, or an empty slug) without a test catching it here, in one
place, instead of relying on each new gateway's author to remember to
re-check every invariant themselves.
"""

from unittest.mock import AsyncMock

import pytest

from investment_agent.domain.models import Recommendation
from investment_agent.gateways.gold.gateway import GoldGateway
from investment_agent.gateways.mutual_fund.gateway import MutualFundGateway
from investment_agent.gateways.mutual_fund.models import MutualFundProduct


def _build_gold_gateway(fake_agent_client, sample_price_snapshot) -> GoldGateway:
    price_adapter = AsyncMock()
    price_adapter.fetch_price.return_value = sample_price_snapshot
    return GoldGateway(agent_client=fake_agent_client, price_adapter=price_adapter)


def _build_mutual_fund_gateway(fake_agent_client, sample_price_snapshot) -> MutualFundGateway:
    price_adapter = AsyncMock()
    price_adapter.fetch_price.return_value = sample_price_snapshot
    price_adapter.last_product = MutualFundProduct.model_validate(
        {
            "isin_code": "IDN000000809",
            "fund_name": "Schroder Dana Prestasi Plus",
            "fund_type": "equity",
            "fund_type_text": "Saham",
            "fund_ccy": "IDR",
            "asset_under_management": 1.0,
            "risk_profile": "High",
            "nav": {"date": "2026-09-16", "value": 31468.57},
            "return_infos": [],
            "investment_manager": {"name": "x", "full_name": "x"},
        }
    )
    return MutualFundGateway(agent_client=fake_agent_client, price_adapter=price_adapter)


# Every gateway registered in main.py::_build_registry() belongs here too -
# add a builder when a new gateway is added, so it's covered by this suite.
GATEWAY_BUILDERS = [_build_gold_gateway, _build_mutual_fund_gateway]
GATEWAY_IDS = ["gold", "mutual_fund"]


@pytest.mark.parametrize("build_gateway", GATEWAY_BUILDERS, ids=GATEWAY_IDS)
async def test_every_gateway_produces_a_valid_asset_analysis(
    build_gateway, fake_agent_client, sample_price_snapshot
) -> None:
    gateway = build_gateway(fake_agent_client, sample_price_snapshot)

    result = await gateway.analyze()

    assert result.current_price == sample_price_snapshot.price
    assert result.price_change_pct == sample_price_snapshot.change_pct
    assert result.recommendation == Recommendation.NEUTRAL
    assert 0.0 <= result.confidence_level <= 1.0
    assert result.technical_summary
    assert result.fundamental_summary
    assert result.risk_scenario
    assert fake_agent_client.received_prompts, "gateway must send a prompt to the agent client"


@pytest.mark.parametrize("build_gateway", GATEWAY_BUILDERS, ids=GATEWAY_IDS)
def test_every_gateway_has_a_non_empty_slug_and_display_name(
    build_gateway, fake_agent_client, sample_price_snapshot
) -> None:
    gateway = build_gateway(fake_agent_client, sample_price_snapshot)

    assert gateway.slug
    assert gateway.display_name
