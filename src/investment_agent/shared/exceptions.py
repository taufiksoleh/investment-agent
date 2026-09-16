"""Application-wide exceptions and their FastAPI error-response mapping.

Kept generic on purpose: nothing here knows about "gold" or any other asset
class. Plugins raise these same exceptions so the API layer has one place to
translate errors into HTTP responses, regardless of which plugin raised them.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class InvestmentAgentError(Exception):
    """Base class for every error raised intentionally by this application."""


class PluginNotFoundError(InvestmentAgentError):
    """Raised when `/analyze/{asset_type}` is called with an unregistered slug."""

    def __init__(self, asset_type: str) -> None:
        self.asset_type = asset_type
        super().__init__(f"No analysis plugin registered for asset type '{asset_type}'.")


class UpstreamPriceUnavailableError(InvestmentAgentError):
    """Raised when a plugin's internal price source can't be reached or is invalid.

    Distinguished from a generic HTTP error so callers get a clear signal that
    the failure is upstream (internal price API), not in our own logic.
    """


class AgentResponseParsingError(InvestmentAgentError):
    """Raised when the Claude Agent SDK response can't be parsed into an AssetAnalysis.

    Reasoning output is free-form text from an LLM; this exception isolates the
    one place that trusts it enough to attempt structured parsing.
    """


def register_exception_handlers(app: FastAPI) -> None:
    """Wire every ``InvestmentAgentError`` subclass to an HTTP response.

    Centralized here so plugins never need to know about status codes or
    FastAPI's response types - they just raise the domain exception.
    """

    @app.exception_handler(PluginNotFoundError)
    async def _handle_plugin_not_found(request: Request, exc: PluginNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(UpstreamPriceUnavailableError)
    async def _handle_upstream_unavailable(
        request: Request, exc: UpstreamPriceUnavailableError
    ) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(AgentResponseParsingError)
    async def _handle_agent_parsing_error(
        request: Request, exc: AgentResponseParsingError
    ) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})
