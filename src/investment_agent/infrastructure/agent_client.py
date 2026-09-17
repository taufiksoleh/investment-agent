"""Generic wrapper around the Claude Agent SDK, used for reasoning only.

Every use case sends its own composed prompt through this single client instead
of importing the SDK directly. That keeps SDK/session/tool wiring in one
place and makes it trivial to inject a fake in tests. This client is never a
source of price data - callers must embed verified prices (from an internal
adapter) into the prompt themselves; the agent only reasons about context
(news, causes, outlook) and optionally uses web search to do so.
"""

import logging
from collections.abc import AsyncIterator, Callable
from typing import Any

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock
from claude_agent_sdk import query as sdk_query

logger = logging.getLogger(__name__)


class ClaudeAgentClient:
    """Runs a single prompt through the Claude Agent SDK and returns its text output."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-5",
        enable_web_search: bool = True,
        verbose: bool = False,
        query_fn: Callable[..., AsyncIterator[Any]] | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._enable_web_search = enable_web_search
        self._verbose = verbose
        # Injectable so unit tests can supply a fake async generator instead of
        # making a real call to the SDK.
        self._query_fn = query_fn or sdk_query

    def _log_stderr(self, line: str) -> None:
        logger.debug("claude-agent-sdk: %s", line.rstrip())

    def _build_options(self) -> ClaudeAgentOptions:
        allowed_tools = ["WebSearch"] if self._enable_web_search else []
        return ClaudeAgentOptions(
            model=self._model,
            allowed_tools=allowed_tools,
            stderr=self._log_stderr if self._verbose else None,
            # The CLI subprocess inherits os.environ, which does NOT include
            # values pydantic-settings only parsed from a local .env file -
            # so the key must be forwarded explicitly or the subprocess has
            # no credentials and hangs on an interactive login prompt.
            env={"ANTHROPIC_API_KEY": self._api_key},
        )

    async def run_analysis(self, prompt: str) -> str:
        """Send `prompt` to the agent and return its concatenated text response.

        The response is returned as raw text; parsing it into a structured
        `AssetAnalysis` is the `Analyzable` use case's job
        (`use_cases/analyze_asset.py`), not this client's - this class only
        knows how to talk to the SDK.
        """
        options = self._build_options()
        chunks: list[str] = []
        async for message in self._query_fn(prompt=prompt, options=options):
            if not isinstance(message, AssistantMessage):
                continue
            for block in message.content:
                if isinstance(block, TextBlock):
                    chunks.append(block.text)
        return "".join(chunks)
