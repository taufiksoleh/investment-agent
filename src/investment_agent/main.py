"""Application entrypoint: builds the FastAPI app and registers every gateway.

This is the ONLY module that imports concrete gateway classes. Adding a new
asset class means adding one block to `_build_registry()` here - nothing in
`api/`, `infrastructure/`, or `use_cases/` changes.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from investment_agent.api.router import router
from investment_agent.gateways.gold.adapter import InternalGoldPriceAdapter
from investment_agent.gateways.gold.gateway import GoldGateway
from investment_agent.gateways.registry import GatewayRegistry
from investment_agent.infrastructure.agent_client import ClaudeAgentClient
from investment_agent.infrastructure.config import Settings, get_settings
from investment_agent.infrastructure.exceptions import register_exception_handlers
from investment_agent.infrastructure.http_client import InternalApiClient
from investment_agent.infrastructure.logger import configure_logging


def _build_registry(settings: Settings) -> GatewayRegistry:
    """Instantiate every gateway and its dependencies, then register them."""
    registry = GatewayRegistry()

    agent_client = ClaudeAgentClient(api_key=settings.anthropic_api_key)
    internal_api_client = InternalApiClient(base_url=settings.internal_price_api_url)

    gold_gateway = GoldGateway(
        agent_client=agent_client,
        price_adapter=InternalGoldPriceAdapter(internal_api_client),
    )
    registry.register(gold_gateway)

    # To add a new asset class (e.g. stock): build its adapter + gateway here
    # and call registry.register(...) - no other file needs to change.

    return registry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Configure logging and build the gateway registry once, at startup."""
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.gateway_registry = _build_registry(settings)
    yield


def create_app() -> FastAPI:
    """Build the FastAPI application with routes and error handlers wired in."""
    app = FastAPI(title="Investment Agent", lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(router)
    return app


app = create_app()
