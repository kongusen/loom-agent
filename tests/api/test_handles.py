"""Test RunHandle operations"""

import asyncio

import pytest
from loom.api import (
    AgentRuntime,
    AgentProfile,
    RunState,
)
from loom.providers.base import LLMProvider, CompletionParams


class MockProvider(LLMProvider):
    """Mock provider for runtime API tests."""

    async def _complete(self, messages, params: CompletionParams | None = None):
        return f"provider-complete:{messages[-1]['content']}"

    async def stream(self, messages, params: CompletionParams | None = None):
        yield "provider"
        yield "-stream"


class TestRunHandle:
    """Test RunHandle operations"""

    @pytest.mark.asyncio
    async def test_run_wait(self):
        """Test run wait"""
        profile = AgentProfile.from_preset("default")
        runtime = AgentRuntime(profile=profile)
        session = runtime.create_session()
        task = session.create_task(goal="Test")
        run = task.start()

        result = await run.wait()
        assert result.state == RunState.COMPLETED
        assert result.summary == "Completed goal: Test"
        assert len(result.events) == 2
        assert result.events[0].type == "run.started"
        assert result.events[-1].type == "run.completed"
        assert len(result.artifacts) == 1

    @pytest.mark.asyncio
    async def test_run_wait_uses_provider(self):
        """Test run wait executes through provider when available."""
        profile = AgentProfile.from_preset("default")
        runtime = AgentRuntime(profile=profile, provider=MockProvider())
        session = runtime.create_session()
        task = session.create_task(goal="Test provider", context={"repo": "loom-agent"})
        run = task.start()

        result = await run.wait()
        assert result.state == RunState.COMPLETED
        assert result.summary.startswith("provider-complete:Goal: Test provider")

    @pytest.mark.asyncio
    async def test_run_events_stream_live(self):
        """Test run events stream through runtime event bus."""
        profile = AgentProfile.from_preset("default")
        runtime = AgentRuntime(profile=profile)
        session = runtime.create_session()
        task = session.create_task(goal="Test stream")
        run = task.start()

        waiter = asyncio.create_task(run.wait())
        received = []
        async for event in run.events():
            received.append(event.type)
            if event.type == "run.completed":
                break

        result = await waiter
        assert result.state == RunState.COMPLETED
        assert received == ["run.started", "run.completed"]

    @pytest.mark.asyncio
    async def test_run_pause_resume(self):
        """Test run pause and resume"""
        profile = AgentProfile.from_preset("default")
        runtime = AgentRuntime(profile=profile)
        session = runtime.create_session()
        task = session.create_task(goal="Test")
        run = task.start()

        run.run.state = RunState.RUNNING
        await run.pause()
        assert run.state == RunState.PAUSED

        await run.resume()
        assert run.state in (RunState.RUNNING, RunState.COMPLETED)

    @pytest.mark.asyncio
    async def test_run_cancel(self):
        """Test run cancel"""
        profile = AgentProfile.from_preset("default")
        runtime = AgentRuntime(profile=profile)
        session = runtime.create_session()
        task = session.create_task(goal="Test")
        run = task.start()

        await run.cancel()
        assert run.state == RunState.CANCELLED

    @pytest.mark.asyncio
    async def test_run_artifacts(self):
        """Test run artifacts"""
        profile = AgentProfile.from_preset("default")
        runtime = AgentRuntime(profile=profile)
        session = runtime.create_session()
        task = session.create_task(goal="Test")
        run = task.start()

        await run.wait()
        artifacts = await run.artifacts()
        assert isinstance(artifacts, list)
        assert len(artifacts) == 1
        stored = runtime.artifact_store.list_by_run(run.id)
        assert len(stored) == 1
        assert stored[0].artifact_id == artifacts[0].artifact_id

    @pytest.mark.asyncio
    async def test_run_transcript_includes_state(self):
        """Test transcript includes run metadata."""
        profile = AgentProfile.from_preset("default")
        runtime = AgentRuntime(profile=profile)
        session = runtime.create_session()
        task = session.create_task(goal="Test")
        run = task.start()

        await run.wait()
        transcript = await run.transcript()
        assert transcript["state"] == RunState.COMPLETED.value
        assert transcript["summary"] == "Completed goal: Test"
