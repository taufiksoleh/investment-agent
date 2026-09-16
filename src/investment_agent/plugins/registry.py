"""Central lookup from asset-type slug to plugin instance.

The API layer only ever talks to this registry, never to a concrete plugin
class - that indirection is what keeps `/analyze/{asset_type}` generic.
"""

from investment_agent.plugins.base import AssetAnalysisPlugin
from investment_agent.shared.exceptions import PluginNotFoundError


class PluginRegistry:
    """A simple name -> plugin map, populated once at startup."""

    def __init__(self) -> None:
        self._plugins: dict[str, AssetAnalysisPlugin] = {}

    def register(self, plugin: AssetAnalysisPlugin) -> None:
        """Add a plugin, keyed by its own `slug`."""
        self._plugins[plugin.slug] = plugin

    def get(self, slug: str) -> AssetAnalysisPlugin:
        """Look up a plugin by slug, or raise `PluginNotFoundError` if unregistered."""
        try:
            return self._plugins[slug]
        except KeyError:
            raise PluginNotFoundError(slug) from None

    def list_slugs(self) -> list[str]:
        """Return every registered slug, sorted for stable output (e.g. in error messages)."""
        return sorted(self._plugins)
