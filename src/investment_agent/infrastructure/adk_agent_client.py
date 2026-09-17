"""Google ADK-based agent client, used for reasoning via LiteLLM-routed
models (DeepSeek by default) as a cheaper alternative to the Claude Agent
SDK.

Implements the same `ReasoningAgent` port (`run_analysis(prompt) -> str`,
see `use_cases/reasoning_agent.py`) as `ClaudeAgentClient`, so gateways never
know or care which one is actually wired in - `build_agent_client()` in this
package picks between them from `Settings.agent_provider`.

Unlike `ClaudeAgentClient`, this client has no web-search tool: ADK's
built-in `google_search` grounding only works with Gemini models, and
LiteLLM-routed models (DeepSeek included) would need a separate search API
wired in as a custom tool, which is out of scope here - the agent reasons
from the prompt text alone.
"""

import logging
from collections.abc import Callable
from typing import Any, Protocol

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.genai import types

logger = logging.getLogger(__name__)

_APP_NAME = "investment-agent"
_USER_ID = "investment-agent"

_INSTRUCTION = (
    "You are a financial reasoning assistant. Follow the user's prompt "
    "exactly and return only what it asks for - typically a single JSON "
    "object, with no extra commentary."
)


class _RunnerLike(Protocol):
    """The subset of `google.adk.runners.Runner` this client relies on."""

    @property
    def session_service(self) -> Any: ...

    def run_async(self, **kwargs: Any) -> Any: ...


class AdkAgentClient:
    """Runs a single prompt through Google ADK and returns its text output."""

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek/deepseek-chat",
        runner_factory: Callable[[LlmAgent], _RunnerLike] | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        # Injectable so unit tests can supply a fake runner instead of
        # making a real call through LiteLLM.
        self._runner_factory = runner_factory or self._default_runner_factory

    @staticmethod
    def _default_runner_factory(agent: LlmAgent) -> InMemoryRunner:
        return InMemoryRunner(agent=agent, app_name=_APP_NAME)

    def _build_agent(self) -> LlmAgent:
        return LlmAgent(
            name="investment_reasoning_agent",
            model=LiteLlm(model=self._model, api_key=self._api_key),
            instruction=_INSTRUCTION,
        )

    async def run_analysis(self, prompt: str) -> str:
        """Send `prompt` to the agent and return its concatenated text response.

        The response is returned as raw text; parsing it into a structured
        `AssetAnalysis` is the `Analyzable` use case's job
        (`use_cases/analyze_asset.py`), not this client's - this class only
        knows how to talk to ADK.
        """
        runner = self._runner_factory(self._build_agent())
        session = await runner.session_service.create_session(
            app_name=_APP_NAME, user_id=_USER_ID
        )
        message = types.Content(role="user", parts=[types.Part(text=prompt)])

        chunks: list[str] = []
        async for event in runner.run_async(
            user_id=_USER_ID, session_id=session.id, new_message=message
        ):
            if not event.is_final_response() or event.content is None:
                continue
            for part in event.content.parts or []:
                if part.text:
                    chunks.append(part.text)
        return "".join(chunks)
