"""Application configuration.

All configuration is loaded from environment variables (optionally via a local
``.env`` file). Nothing here is hardcoded, so the same image can be deployed
against different internal APIs / API keys purely through env vars.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed view over the environment variables the app needs to run."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Which reasoning backend `infrastructure.agent_client_factory` wires up:
    # "claude" (Claude Agent SDK, needs anthropic_api_key) or "deepseek"
    # (Google ADK + LiteLLM routed to DeepSeek, needs deepseek_api_key) -
    # DeepSeek is the default since it's the whole point of this switch:
    # a much cheaper backend, with Claude kept available as a fallback.
    agent_provider: Literal["claude", "deepseek"] = Field(
        default="deepseek", validation_alias="AGENT_PROVIDER"
    )

    # Named distinctly from ANTHROPIC_API_KEY (which the Claude Agent SDK's
    # CLI subprocess expects, see agent_client.py) so it doesn't collide with
    # a developer's own ANTHROPIC_API_KEY set locally for the Claude Code CLI.
    anthropic_api_key: str = Field(
        default="", validation_alias="INVESTMENT_AGENT_ANTHROPIC_API_KEY"
    )
    # DeepSeek's OpenAI-compatible API key, used by the Google ADK client
    # (infrastructure/adk_agent_client.py) via LiteLLM's "deepseek/" routing.
    deepseek_api_key: str = Field(default="", validation_alias="DEEPSEEK_API_KEY")
    # LiteLLM model id - "deepseek/deepseek-chat" (general reasoning) or
    # "deepseek/deepseek-reasoner" (heavier chain-of-thought, pricier/slower).
    deepseek_model: str = Field(
        default="deepseek/deepseek-chat", validation_alias="DEEPSEEK_MODEL"
    )
    # Defaults to BMoney's public bullion price API (the gold gateway's data
    # source); override per-environment/asset-class needs via env var.
    internal_price_api_url: str = "https://api.bmoney.id"
    # BMoney's mutual-fund products endpoint lists ~40 funds; the default
    # mutual fund gateway tracks exactly one (mirrors gold tracking one
    # commodity), addressed by BMoney's own numeric product id (the same
    # id used in /products/{id} and /products/{id}/navs). Defaults to
    # Schroder Dana Prestasi Plus, a long-established equity fund present
    # in BMoney's product list - override per deployment.
    mutual_fund_product_id: int = Field(
        default=46, validation_alias="INVESTMENT_AGENT_MUTUAL_FUND_PRODUCT_ID"
    )
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached ``Settings`` instance.

    Cached so env vars are parsed once and every module (config, gateways,
    clients) shares the same values instead of re-reading the environment.
    """
    return Settings()
