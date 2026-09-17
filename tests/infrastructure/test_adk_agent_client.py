"""Unit tests for `AdkAgentClient`, using a fake ADK runner so no real call
goes through Google ADK/LiteLLM/DeepSeek."""

from google.genai import types

from investment_agent.infrastructure.adk_agent_client import AdkAgentClient


class FakeSession:
    def __init__(self, session_id: str = "fake-session") -> None:
        self.id = session_id


class FakeSessionService:
    async def create_session(self, *, app_name: str, user_id: str) -> FakeSession:
        return FakeSession()


class FakeEvent:
    def __init__(self, text: str | None, final: bool = True) -> None:
        self._final = final
        self.content = types.Content(parts=[types.Part(text=text)]) if text is not None else None

    def is_final_response(self) -> bool:
        return self._final


class FakeRunner:
    """Stand-in for `google.adk.runners.InMemoryRunner`."""

    def __init__(self, events: list[FakeEvent]) -> None:
        self.session_service = FakeSessionService()
        self._events = events
        self.received_kwargs: dict | None = None

    async def run_async(self, **kwargs):
        self.received_kwargs = kwargs
        for event in self._events:
            yield event


async def test_run_analysis_returns_concatenated_final_response_text():
    events = [
        FakeEvent("partial chunk", final=False),
        FakeEvent('{"key": "value"}', final=True),
    ]
    runner = FakeRunner(events)
    client = AdkAgentClient(api_key="fake-key", runner_factory=lambda agent: runner)

    result = await client.run_analysis("analyze this")

    assert result == '{"key": "value"}'


async def test_run_analysis_ignores_non_final_events():
    events = [FakeEvent("should be ignored", final=False)]
    runner = FakeRunner(events)
    client = AdkAgentClient(api_key="fake-key", runner_factory=lambda agent: runner)

    result = await client.run_analysis("analyze this")

    assert result == ""


async def test_run_analysis_passes_prompt_as_user_message():
    runner = FakeRunner([FakeEvent("ok")])
    client = AdkAgentClient(api_key="fake-key", runner_factory=lambda agent: runner)

    await client.run_analysis("what is the outlook?")

    assert runner.received_kwargs is not None
    message = runner.received_kwargs["new_message"]
    assert message.role == "user"
    assert message.parts[0].text == "what is the outlook?"
