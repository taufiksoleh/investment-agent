"""Tests for MutualFundGateway, exercising the generic `analyze()` flow
defined in the `Analyzable` use case with fake price/agent dependencies
injected."""

from unittest.mock import AsyncMock

import pytest
import respx
from httpx import Response

from investment_agent.domain.models import Recommendation
from investment_agent.gateways.mutual_fund.gateway import MutualFundGateway
from investment_agent.gateways.mutual_fund.models import MutualFundProduct
from investment_agent.infrastructure.exceptions import UpstreamPriceUnavailableError
from investment_agent.infrastructure.http_client import InternalApiClient

_PRODUCT_DETAIL_RESPONSE = {
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
_NAV_HISTORY_RESPONSE = {
    "data": [
        {"date": "2026-09-16", "value": 1761.5239},
        {"date": "2026-09-15", "value": 1761.194},
    ]
}


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


async def test_analyze_merges_price_snapshot_and_agent_reasoning(
    fake_agent_client, sample_price_snapshot
) -> None:
    price_adapter = AsyncMock()
    price_adapter.fetch_price.return_value = sample_price_snapshot
    price_adapter.last_product = _sample_product()

    gateway = MutualFundGateway(agent_client=fake_agent_client, price_adapter=price_adapter)

    result = await gateway.analyze()

    assert result.current_price == sample_price_snapshot.price
    assert result.price_change_pct == sample_price_snapshot.change_pct
    assert result.recommendation == Recommendation.NEUTRAL
    assert fake_agent_client.received_prompts, "gateway must send a prompt to the agent client"


def test_build_prompt_raises_when_price_not_fetched_yet(
    fake_agent_client, sample_price_snapshot
) -> None:
    price_adapter = AsyncMock()
    price_adapter.last_product = None
    gateway = MutualFundGateway(agent_client=fake_agent_client, price_adapter=price_adapter)

    with pytest.raises(UpstreamPriceUnavailableError):
        gateway.build_prompt(sample_price_snapshot)


@respx.mock
async def test_for_product_assembles_a_working_gateway_for_the_given_id(
    fake_agent_client,
) -> None:
    respx.get("http://internal-api.test/_exclusive/bmoney/mutual-fund/products/115").mock(
        return_value=Response(200, json=_PRODUCT_DETAIL_RESPONSE)
    )
    respx.get("http://internal-api.test/_exclusive/bmoney/mutual-fund/products/115/navs").mock(
        return_value=Response(200, json=_NAV_HISTORY_RESPONSE)
    )
    http_client = InternalApiClient(base_url="http://internal-api.test")

    gateway = MutualFundGateway.for_product(115, fake_agent_client, http_client)
    result = await gateway.analyze()

    assert gateway.slug == "mutual-fund"
    assert result.current_price == _PRODUCT_DETAIL_RESPONSE["data"]["nav"]["value"]
