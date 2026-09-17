"""Unit tests for `build_agent_client`'s provider switch - no real Claude/DeepSeek
call happens here, construction alone is exercised."""

from investment_agent.infrastructure.adk_agent_client import AdkAgentClient
from investment_agent.infrastructure.agent_client import ClaudeAgentClient
from investment_agent.infrastructure.agent_client_factory import build_agent_client
from investment_agent.infrastructure.config import Settings


def _settings(**overrides) -> Settings:
    # Settings fields use validation_alias (env var names), so construction
    # must use those aliases, not the snake_case attribute names.
    defaults = {
        "AGENT_PROVIDER": "deepseek",
        "INVESTMENT_AGENT_ANTHROPIC_API_KEY": "",
        "DEEPSEEK_API_KEY": "",
        "DEEPSEEK_MODEL": "deepseek/deepseek-chat",
    }
    return Settings(**{**defaults, **overrides})


def test_defaults_to_deepseek_backend():
    client = build_agent_client(_settings(DEEPSEEK_API_KEY="ds-key"))
    assert isinstance(client, AdkAgentClient)


def test_claude_provider_returns_claude_client():
    client = build_agent_client(
        _settings(AGENT_PROVIDER="claude", INVESTMENT_AGENT_ANTHROPIC_API_KEY="ak-key")
    )
    assert isinstance(client, ClaudeAgentClient)


def test_deepseek_model_override_is_forwarded():
    client = build_agent_client(
        _settings(DEEPSEEK_API_KEY="ds-key", DEEPSEEK_MODEL="deepseek/deepseek-reasoner")
    )
    assert isinstance(client, AdkAgentClient)
    assert client._model == "deepseek/deepseek-reasoner"
