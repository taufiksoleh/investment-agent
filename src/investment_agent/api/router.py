"""The single generic analysis endpoint.

There is intentionally no per-asset-class route (no `/analyze/gold`,
`/analyze/stock`, ...). Every asset type goes through this one endpoint,
which resolves the plugin via the registry - adding a new asset class never
requires touching this file.
"""

from fastapi import APIRouter, Depends, Request

from investment_agent.domain.models import AssetAnalysis
from investment_agent.gateways.registry import PluginRegistry

router = APIRouter()


def get_registry(request: Request) -> PluginRegistry:
    """Fetch the app-wide plugin registry set up at startup (see `main.py`)."""
    return request.app.state.plugin_registry


@router.get("/analyze/{asset_type}", response_model=AssetAnalysis)
async def analyze_asset(
    asset_type: str,
    registry: PluginRegistry = Depends(get_registry),
) -> AssetAnalysis:
    """Run analysis for `asset_type` (e.g. "gold") and return the result.

    Raises a 404 (via `PluginNotFoundError`'s exception handler) when
    `asset_type` has no registered plugin.
    """
    plugin = registry.get(asset_type)
    return await plugin.analyze()
