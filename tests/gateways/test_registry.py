"""Tests for GatewayRegistry: slug lookup and capability-aware require()."""

from unittest.mock import AsyncMock

import pytest

from investment_agent.gateways.gold.gateway import GoldGateway
from investment_agent.gateways.registry import GatewayRegistry
from investment_agent.infrastructure.exceptions import (
    GatewayNotFoundError,
    UseCaseNotSupportedError,
)
from investment_agent.use_cases.analyze_asset import Analyzable
from investment_agent.use_cases.asset_gateway import AssetGateway


class _PriceOnlyGateway:
    """Implements AssetGateway but not Analyzable - exercises require()'s capability check."""

    slug = "price-only"
    display_name = "Price Only"

    async def get_current_price(self):
        raise NotImplementedError


def test_get_raises_for_unregistered_slug() -> None:
    registry = GatewayRegistry()

    with pytest.raises(GatewayNotFoundError):
        registry.get("nonexistent")


def test_require_returns_gateway_when_port_is_supported(fake_agent_client) -> None:
    registry = GatewayRegistry()
    gateway = GoldGateway(agent_client=fake_agent_client, price_adapter=AsyncMock())
    registry.register(gateway)

    result = registry.require("gold", Analyzable)

    assert result is gateway


def test_require_raises_use_case_not_supported_for_missing_capability() -> None:
    registry = GatewayRegistry()
    registry.register(_PriceOnlyGateway())

    with pytest.raises(UseCaseNotSupportedError):
        registry.require("price-only", Analyzable)


def test_require_raises_gateway_not_found_for_unregistered_slug() -> None:
    registry = GatewayRegistry()

    with pytest.raises(GatewayNotFoundError):
        registry.require("nonexistent", Analyzable)


def test_price_only_gateway_satisfies_asset_gateway_protocol() -> None:
    assert isinstance(_PriceOnlyGateway(), AssetGateway)
