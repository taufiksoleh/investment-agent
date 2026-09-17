"""Central lookup from asset-type slug to gateway instance.

The API layer only ever talks to this registry, never to a concrete gateway
class - that indirection is what keeps `/analyze/{asset_type}` generic.
"""

from investment_agent.infrastructure.exceptions import GatewayNotFoundError
from investment_agent.use_cases.analyze_asset import Analyzable


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

    def list_slugs(self) -> list[str]:
        """Return every registered slug, sorted for stable output (e.g. in error messages)."""
        return sorted(self._gateways)
