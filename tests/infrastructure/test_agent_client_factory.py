"""Unit tests for `build_agent_client`'s provider switch - no real Claude or
OpenAI-compatible-endpoint call happens here, construction alone is exercised."""

from investment_agent.infrastructure.adk_agent_client import AdkAgentClient
from investment_agent.infrastructure.agent_client import ClaudeAgentClient
from investment_agent.infrastructure.agent_client_factory import build_agent_client
from investment_agent.infrastructure.config import Settings


def _settings(**overrides) -> Settings:
    # Settings fields use validation_alias (env var names), so construction
    # must use those aliases, not the snake_case attribute names.
    defaults = {
        "AGENT_PROVIDER": "openai_compatible",
        "INVESTMENT_AGENT_ANTHROPIC_API_KEY": "",
        "OPENAI_COMPATIBLE_API_KEY": "",
        "OPENAI_COMPATIBLE_BASE_URL": "",
        "OPENAI_COMPATIBLE_MODEL": "",
    }
    return Settings(**{**defaults, **overrides})


def test_defaults_to_openai_compatible_backend():
    client = build_agent_client(_settings(OPENAI_COMPATIBLE_API_KEY="some-key"))
    assert isinstance(client, AdkAgentClient)


def test_claude_provider_returns_claude_client():
    client = build_agent_client(
        _settings(AGENT_PROVIDER="claude", INVESTMENT_AGENT_ANTHROPIC_API_KEY="ak-key")
    )
    assert isinstance(client, ClaudeAgentClient)


def test_openai_compatible_settings_are_forwarded():
    client = build_agent_client(
        _settings(
            OPENAI_COMPATIBLE_API_KEY="some-key",
            OPENAI_COMPATIBLE_BASE_URL="https://api.deepseek.com/v1",
            OPENAI_COMPATIBLE_MODEL="deepseek-chat",
        )
    )
    assert isinstance(client, AdkAgentClient)
    assert client._api_key == "some-key"
    assert client._base_url == "https://api.deepseek.com/v1"
    assert client._model == "deepseek-chat"
