"""Application entrypoint: builds the FastAPI app and registers every gateway.

This is the ONLY module that imports concrete gateway classes. Adding a new
asset class means adding one block to `_build_registry()` here - nothing in
`api/`, `infrastructure/`, or `use_cases/` changes.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from investment_agent.api.middleware import add_request_id_middleware
from investment_agent.api.mutual_fund_router import router as mutual_fund_router
from investment_agent.api.router import router
from investment_agent.gateways.gold.adapter import InternalGoldPriceAdapter
from investment_agent.gateways.gold.gateway import GoldGateway
from investment_agent.gateways.mutual_fund.adapter import InternalMutualFundPriceAdapter
from investment_agent.gateways.mutual_fund.gateway import MutualFundGateway
from investment_agent.gateways.registry import GatewayRegistry
from investment_agent.infrastructure.agent_client import ClaudeAgentClient
from investment_agent.infrastructure.config import Settings, get_settings
from investment_agent.infrastructure.exceptions import register_exception_handlers
from investment_agent.infrastructure.http_client import InternalApiClient
from investment_agent.infrastructure.logger import configure_logging


def _build_registry(
    settings: Settings,
    agent_client: ClaudeAgentClient,
    internal_api_client: InternalApiClient,
) -> GatewayRegistry:
    """Instantiate every gateway and register it, sharing the given infra clients."""
    registry = GatewayRegistry()

    gold_gateway = GoldGateway(
        agent_client=agent_client,
        price_adapter=InternalGoldPriceAdapter(internal_api_client),
    )
    registry.register(gold_gateway)

    # Same BMoney domain as gold, different endpoint - shares internal_api_client.
    mutual_fund_gateway = MutualFundGateway(
        agent_client=agent_client,
        price_adapter=InternalMutualFundPriceAdapter(
            internal_api_client, product_id=settings.mutual_fund_product_id
        ),
    )
    registry.register(mutual_fund_gateway)

    # To add a new asset class (e.g. stock): build its adapter + gateway here
    # and call registry.register(...) - no other file needs to change.

    return registry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Configure logging and build shared infra clients + the gateway registry once, at startup.

    `agent_client`/`internal_api_client` are stored on `app.state` (not just
    passed into `_build_registry()`) so routes that need a gateway built
    per-request - e.g. `/analyze/mutual-fund/{product_id}` - can reuse the
    same instances instead of opening new HTTP connections per request.
    """
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.agent_client = ClaudeAgentClient(api_key=settings.anthropic_api_key)
    app.state.internal_api_client = InternalApiClient(base_url=settings.internal_price_api_url)
    app.state.gateway_registry = _build_registry(
        settings, app.state.agent_client, app.state.internal_api_client
    )
    yield
    await app.state.internal_api_client.aclose()


def create_app() -> FastAPI:
    """Build the FastAPI application with routes and error handlers wired in."""
    app = FastAPI(title="Investment Agent", lifespan=lifespan)
    register_exception_handlers(app)
    add_request_id_middleware(app)
    app.include_router(router)
    app.include_router(mutual_fund_router)
    return app


app = create_app()
