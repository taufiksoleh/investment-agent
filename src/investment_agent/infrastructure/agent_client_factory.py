"""Picks which `ReasoningAgent` backs the app, based on `Settings.agent_provider`.

The only place that knows both `ClaudeAgentClient` and `AdkAgentClient`
exist - everything downstream (gateways, use cases) depends on the
`ReasoningAgent` port (`use_cases/reasoning_agent.py`) and never imports
either concrete client directly.
"""

from investment_agent.infrastructure.adk_agent_client import AdkAgentClient
from investment_agent.infrastructure.agent_client import ClaudeAgentClient
from investment_agent.infrastructure.config import Settings
from investment_agent.use_cases.reasoning_agent import ReasoningAgent


def build_agent_client(settings: Settings) -> ReasoningAgent:
    """Construct the configured reasoning agent client.

    `settings.agent_provider` selects the backend:
    - "deepseek" (default): Google ADK, routed via LiteLLM to DeepSeek's
      OpenAI-compatible API - much cheaper than Claude, no web search tool.
    - "claude": the Claude Agent SDK, with web search enabled.

    Construction never validates the API key's presence (mirrors
    `ClaudeAgentClient`'s existing behavior) - an empty key surfaces as an
    auth error from the provider the first time `run_analysis()` is
    actually called, not at app startup. This keeps gateway/app construction
    usable in tests that never make a real call.
    """
    if settings.agent_provider == "claude":
        return ClaudeAgentClient(api_key=settings.anthropic_api_key)
    return AdkAgentClient(api_key=settings.deepseek_api_key, model=settings.deepseek_model)
