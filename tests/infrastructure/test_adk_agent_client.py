"""Unit tests for `AdkAgentClient`, using a fake ADK runner so no real call
goes through Google ADK/LiteLLM or any OpenAI-compatible endpoint."""

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


def _client(
    events: list[FakeEvent],
    captured_agents: list | None = None,
    captured_runners: list | None = None,
) -> AdkAgentClient:
    def runner_factory(agent):
        if captured_agents is not None:
            captured_agents.append(agent)
        runner = FakeRunner(events)
        if captured_runners is not None:
            captured_runners.append(runner)
        return runner

    return AdkAgentClient(
        api_key="fake-key",
        model="some-model",
        base_url="https://example.com/v1",
        runner_factory=runner_factory,
    )


async def test_run_analysis_returns_concatenated_final_response_text():
    events = [
        FakeEvent("partial chunk", final=False),
        FakeEvent('{"key": "value"}', final=True),
    ]
    client = _client(events)

    result = await client.run_analysis("analyze this")

    assert result == '{"key": "value"}'


async def test_run_analysis_ignores_non_final_events():
    client = _client([FakeEvent("should be ignored", final=False)])

    result = await client.run_analysis("analyze this")

    assert result == ""


async def test_run_analysis_passes_prompt_as_user_message():
    captured_runners: list = []
    client = _client([FakeEvent("ok")], captured_runners=captured_runners)

    await client.run_analysis("what is the outlook?")

    runner = captured_runners[0]
    assert runner.received_kwargs is not None
    message = runner.received_kwargs["new_message"]
    assert message.role == "user"
    assert message.parts[0].text == "what is the outlook?"


async def test_routes_via_generic_openai_compatible_litellm_model():
    """Any OpenAI-compatible endpoint is reached through LiteLLM's generic
    "openai/<model>" custom-provider form with an explicit api_base - never
    a provider-specific LiteLLM prefix - so this works for any provider that
    speaks the OpenAI chat-completions API, not just ones LiteLLM special-cases."""
    captured_agents: list = []
    client = _client([FakeEvent("ok")], captured_agents=captured_agents)

    await client.run_analysis("prompt")

    assert len(captured_agents) == 1
    litellm_model = captured_agents[0].model
    assert litellm_model.model == "openai/some-model"
    assert litellm_model._additional_args["api_key"] == "fake-key"
    assert litellm_model._additional_args["api_base"] == "https://example.com/v1"
