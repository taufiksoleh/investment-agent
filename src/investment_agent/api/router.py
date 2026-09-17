"""The single generic analysis endpoint.

There is intentionally no per-asset-class route (no `/analyze/gold`,
`/analyze/stock`, ...). Every asset type goes through this one endpoint,
which resolves the gateway via the registry - adding a new asset class never
requires touching this file.
"""

from fastapi import APIRouter, Depends, Request

from investment_agent.domain.models import AssetAnalysis
from investment_agent.gateways.registry import GatewayRegistry

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness endpoint for orchestrator readiness checks (load balancers, k8s, ECS)."""
    return {"status": "ok"}


def get_registry(request: Request) -> GatewayRegistry:
    """Fetch the app-wide gateway registry set up at startup (see `main.py`)."""
    return request.app.state.gateway_registry


@router.get("/analyze/{asset_type}", response_model=AssetAnalysis)
async def analyze_asset(
    asset_type: str,
    registry: GatewayRegistry = Depends(get_registry),
) -> AssetAnalysis:
    """Run analysis for `asset_type` (e.g. "gold") and return the result.

    Raises a 404 (via `GatewayNotFoundError`'s exception handler) when
    `asset_type` has no registered gateway.
    """
    gateway = registry.get(asset_type)
    return await gateway.analyze()
