"""Central lookup from asset-type slug to gateway instance.

The API layer only ever talks to this registry, never to a concrete gateway
class - that indirection is what keeps `/analyze/{asset_type}` generic.
"""

from typing import TypeVar

from investment_agent.infrastructure.exceptions import (
    GatewayNotFoundError,
    UseCaseNotSupportedError,
)
from investment_agent.use_cases.analyze_asset import Analyzable

PortT = TypeVar("PortT")


class GatewayRegistry:
    """A simple slug -> gateway map, populated once at startup."""

    def __init__(self) -> None:
        self._gateways: dict[str, Analyzable] = {}

    def register(self, gateway: Analyzable) -> None:
        """Add a gateway, keyed by its own `slug`."""
        self._gateways[gateway.slug] = gateway

    def get(self, slug: str) -> Analyzable:
        """Look up a gateway by slug, or raise `GatewayNotFoundError` if unregistered."""
        try:
            return self._gateways[slug]
        except KeyError:
            raise GatewayNotFoundError(slug) from None

    def require(self, slug: str, port: type[PortT]) -> PortT:
        """Look up a gateway by slug and assert it implements `port`.

        Raises `GatewayNotFoundError` if the slug isn't registered at all, or
        `UseCaseNotSupportedError` if it's registered but doesn't implement
        the requested port (e.g. a gateway with no news support once that use
        case exists). This is what lets a controller for any future use case
        stay generic without every gateway being forced to implement every
        use case - unlike `get()`, which assumes every gateway is `Analyzable`.
        """
        gateway = self.get(slug)
        if not isinstance(gateway, port):
            raise UseCaseNotSupportedError(slug, port.__name__)
        return gateway

    def list_slugs(self) -> list[str]:
        """Return every registered slug, sorted for stable output (e.g. in error messages)."""
        return sorted(self._gateways)
