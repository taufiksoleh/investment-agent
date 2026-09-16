"""Application configuration.

All configuration is loaded from environment variables (optionally via a local
``.env`` file). Nothing here is hardcoded, so the same image can be deployed
against different internal APIs / API keys purely through env vars.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed view over the environment variables the app needs to run."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str = ""
    internal_price_api_url: str = "http://localhost:9000"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached ``Settings`` instance.

    Cached so env vars are parsed once and every module (config, plugins,
    clients) shares the same values instead of re-reading the environment.
    """
    return Settings()
