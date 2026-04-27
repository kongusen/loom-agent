"""Tests for the public runtime signal adapter contract."""

import pytest

from loom import Agent, Model, RuntimeSignal, SessionConfig, SignalAdapter


def test_signal_adapter_converts_external_events_to_runtime_signal() -> None:
    adapter = SignalAdapter(
        source="gateway:slack",
        type="message",
        summary=lambda event: event["text"],
        payload=lambda event: {
            "channel": event["channel"],
            "thread_ts": event["thread_ts"],
        },
        dedupe_key=lambda event: event["event_id"],
    )

    signal = adapter.adapt(
        {
            "event_id": "evt-1",
            "text": "Deployment failed in staging",
            "channel": "deployments",
            "thread_ts": "1710000000.000001",
        }
    )

    assert isinstance(signal, RuntimeSignal)
    assert signal.source == "gateway:slack"
    assert signal.type == "message"
    assert signal.summary == "Deployment failed in staging"
    assert signal.payload["channel"] == "deployments"
    assert signal.payload["thread_ts"] == "1710000000.000001"
    assert signal.payload["content"] == "Deployment failed in staging"
    assert signal.dedupe_key == "evt-1"


@pytest.mark.asyncio
async def test_session_receive_uses_adapter_without_distinguishing_producers() -> None:
    agent = Agent(model=Model.openai("gpt-test"))
    session = agent.session(SessionConfig(id="ops"))
    cron = SignalAdapter(
        source="cron",
        type="job",
        summary=lambda event: f"Run job {event['job_id']}",
        payload=lambda event: {"job_id": event["job_id"]},
    )

    decision = await session.receive({"job_id": "nightly-health-check"}, adapter=cron)

    assert decision.action == "run"
    assert session._pending_signals[0].source == "cron"
    assert session._pending_signals[0].type == "job"
    assert session._pending_signals[0].summary == "Run job nightly-health-check"


@pytest.mark.asyncio
async def test_agent_receive_allows_call_site_overrides() -> None:
    agent = Agent(model=Model.openai("gpt-test"))
    heartbeat = SignalAdapter(
        source="heartbeat",
        type="monitor",
        urgency="low",
        summary=lambda event: event["summary"],
    )

    decision = await agent.receive(
        {"summary": "CPU usage exceeded 90%"},
        adapter=heartbeat,
        urgency="high",
        session_id="ops",
        dedupe_key="cpu-high",
    )

    session = agent.session(SessionConfig(id="ops"))

    assert decision.action == "interrupt"
    assert session._pending_signals[0].urgency == "high"
    assert session._pending_signals[0].dedupe_key == "cpu-high"


@pytest.mark.asyncio
async def test_signal_adapter_events_enter_runtime_context() -> None:
    from loom.providers.base import CompletionRequest, CompletionResponse, LLMProvider

    class DashboardAwareProvider(LLMProvider):
        def __init__(self) -> None:
            super().__init__()
            self.requests: list[CompletionRequest] = []

        async def _complete_request(self, request: CompletionRequest) -> CompletionResponse:
            self.requests.append(request)
            return CompletionResponse(content="handled")

    provider = DashboardAwareProvider()
    agent = Agent(model=Model.openai("gpt-test"))
    agent._provider = provider
    agent._provider_resolved = True

    session = agent.session(SessionConfig(id="runtime-signals"))
    gateway = SignalAdapter(
        source="gateway:slack",
        type="message",
        summary=lambda event: event["text"],
        payload=lambda event: {"channel": event["channel"]},
    )
    cron = SignalAdapter(
        source="cron",
        type="job",
        summary=lambda event: f"Run scheduled job {event['job_id']}",
        payload=lambda event: {"job_id": event["job_id"]},
    )

    await session.receive(
        {"text": "Customer asks for deployment status", "channel": "support"},
        adapter=gateway,
    )
    await session.receive(
        {"job_id": "deployment-health"},
        adapter=cron,
        urgency="high",
    )

    result = await session.run("Handle pending runtime signals")

    rendered = "\n".join(str(message["content"]) for message in provider.requests[0].messages)
    assert result.output == "handled"
    assert "## Pending Events" in rendered
    assert "Customer asks for deployment status" in rendered
    assert "Run scheduled job deployment-health" in rendered
    assert "## Active Risks" in rendered
