"""The port `Analyzable` depends on for reasoning about a verified price.

Kept separate from any concrete SDK (Claude Agent SDK, Google ADK, ...) so
`analyze_asset.py` never has to know which one is actually wired in -
`main.py`'s agent-client factory decides that from configuration alone.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ReasoningAgent(Protocol):
    """Structural port: anything that can turn a prompt into text reasoning."""

    async def run_analysis(self, prompt: str) -> str:
        """Send `prompt` to the underlying model and return its raw text response.

        Must never be a source of price data - callers embed verified prices
        into the prompt themselves; this only returns reasoning/context text.
        """
        ...
