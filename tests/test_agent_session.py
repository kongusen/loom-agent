"""Tests for stateful sessions in the public Agent API."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from loom import Agent, Model, RunContext, SessionConfig
from loom.config import AgentConfig
from loom.runtime import RunState, Session


def test_session_reuse_by_id():
    agent = Agent(config=AgentConfig(model=Model.anthropic("claude-sonnet-4")))

    first = agent.session(SessionConfig(id="demo"))
    second = agent.session(SessionConfig(id="demo"))

    assert isinstance(first, Session)
    assert first is second


@pytest.mark.asyncio
async def test_session_run_tracks_runs():
    with patch("loom.agent._resolve_provider", return_value=None):
        agent = Agent(config=AgentConfig(model=Model.anthropic("claude-sonnet-4")))
        session = agent.session(SessionConfig(id="demo"))

        result_one = await session.run("First task")
        result_two = await session.run("Second task", context=RunContext(inputs={"step": 2}))

    runs = session.list_runs()
    assert len(runs) == 2
    assert result_one.state == RunState.COMPLETED
    assert result_two.state == RunState.COMPLETED
    assert runs[0].prompt == "First task"
    assert runs[1].prompt == "Second task"


@pytest.mark.asyncio
async def test_run_transcript_includes_output():
    with patch("loom.agent._resolve_provider", return_value=None):
        agent = Agent(config=AgentConfig(model=Model.anthropic("claude-sonnet-4")))
        run = agent.session(SessionConfig(id="demo")).start("Inspect the codebase")

        await run.wait()
        transcript = await run.transcript()

    assert transcript["state"] == RunState.COMPLETED.value
    assert transcript["output"] == "Completed goal: Inspect the codebase"
    assert transcript["prompt"] == "Inspect the codebase"


def test_session_reuse_merges_metadata():
    agent = Agent(config=AgentConfig(model=Model.anthropic("claude-sonnet-4")))

    first = agent.session(SessionConfig(id="demo", metadata={"tenant": "acme"}))
    second = agent.session(SessionConfig(id="demo", metadata={"plan": "pro"}))

    assert first is second
    assert second.metadata == {"tenant": "acme", "plan": "pro"}


def test_session_ttl_evicts_expired_session():
    agent = Agent(config=AgentConfig(model=Model.anthropic("claude-sonnet-4")))

    stale = agent.session(SessionConfig(id="stale"))
    stale.created_at = datetime.now() - timedelta(hours=30)

    evicted = agent._evict_old_sessions()

    assert evicted == 1
    assert stale._closed is True
    assert "stale" not in agent._sessions


def test_session_rebuilds_after_ttl_eviction():
    agent = Agent(config=AgentConfig(model=Model.anthropic("claude-sonnet-4")))

    first = agent.session(SessionConfig(id="demo"))
    first.created_at = datetime.now() - timedelta(hours=30)

    second = agent.session(SessionConfig(id="demo"))

    assert second is not first
    assert second.id == "demo"
