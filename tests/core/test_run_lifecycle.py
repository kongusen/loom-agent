"""Tests for the shared run lifecycle coordinator."""

from unittest.mock import MagicMock

import pytest

from loom.runtime.engine import AgentEngine, EngineConfig
from loom.runtime.loop_runner import LoopDone
from loom.runtime.run_lifecycle import RunLifecycleRuntime
from loom.types.stream import DoneEvent


def _lifecycle() -> tuple[RunLifecycleRuntime, dict[str, list]]:
    calls: dict[str, list] = {
        "initialize": [],
        "history": [],
        "drain": [],
        "load": [],
        "semantic": [],
        "provider": [],
        "save": [],
        "sync": [],
        "start": [],
        "stop": [],
    }
    context_manager = MagicMock()
    context_manager.current_goal = None
    context_runtime = MagicMock()
    ecosystem_manager = MagicMock()
    ecosystem_manager.get_system_prompt_additions.return_value = "mcp prompt"
    memory_runtime = MagicMock()
    memory_runtime.semantic_memory = object()
    memory_runtime.provider_system_prompt.return_value = "provider prompt"
    memory_runtime.sync_memory_providers.side_effect = lambda goal, output, session_id: calls[
        "sync"
    ].append((goal, output, session_id))
    heartbeat = MagicMock()
    heartbeat.start.side_effect = lambda handler: calls["start"].append(handler)
    heartbeat.stop.side_effect = lambda: calls["stop"].append(True)

    runtime = RunLifecycleRuntime(
        config=MagicMock(enable_memory=True),
        context_manager=context_manager,
        context_runtime=context_runtime,
        ecosystem_manager=ecosystem_manager,
        heartbeat=heartbeat,
        memory_runtime=memory_runtime,
        memory_enabled=lambda: True,
        drain_signals=lambda: calls["drain"].append(True),
        heartbeat_handler=lambda *_args: None,
    )
    context_runtime.initialize_context.side_effect = lambda *args: calls["initialize"].append(args)
    context_runtime.inject_session_history.side_effect = lambda history: calls["history"].append(
        history
    )
    memory_runtime.load_session_memory.side_effect = lambda session_id: calls["load"].append(
        session_id
    )
    memory_runtime.inject_semantic_memories.side_effect = lambda goal: calls["semantic"].append(
        goal
    )
    memory_runtime.inject_provider_memories.side_effect = lambda goal, session_id: calls[
        "provider"
    ].append((goal, session_id))
    memory_runtime.save_session_memory.side_effect = lambda session_id: calls["save"].append(
        session_id
    )
    return runtime, calls


def test_run_lifecycle_prepare_finalize_and_stop_order() -> None:
    runtime, calls = _lifecycle()

    prepared = runtime.prepare(
        goal="ship",
        instructions="base",
        context={"repo": "loom"},
        session_id="s1",
        history=[{"role": "user", "content": "hi"}],
    )
    runtime.finalize_success(prepared, "done")
    runtime.stop()

    assert prepared.instructions == "base\n\nmcp prompt\n\nprovider prompt"
    assert calls["initialize"][0] == ("ship", prepared.instructions, {"repo": "loom"})
    assert calls["history"][0] == [{"role": "user", "content": "hi"}]
    assert calls["drain"] == [True]
    assert calls["load"] == ["s1"]
    assert calls["semantic"] == ["ship"]
    assert calls["provider"] == [("ship", "s1")]
    assert calls["save"] == ["s1"]
    assert calls["sync"] == [("ship", "done", "s1")]
    assert len(calls["start"]) == 1
    assert calls["stop"] == [True]


@pytest.mark.asyncio
async def test_agent_engine_batch_and_streaming_share_run_lifecycle() -> None:
    engine = AgentEngine(provider=MagicMock(), config=EngineConfig(enable_memory=False))
    prepared = MagicMock(goal="ship", instructions="merged", context=None, session_id=None)
    engine.run_lifecycle.prepare = MagicMock(return_value=prepared)
    engine.run_lifecycle.finalize_success = MagicMock()
    engine.run_lifecycle.stop = MagicMock()

    async def _run_harness(*_args, **_kwargs):
        return {"status": "success", "output": "batch", "events": [], "iterations": 1}

    async def _run_loop_core(_goal, *, stream, token_callback=None):
        assert stream is True
        assert token_callback is None
        yield LoopDone(status="success", output="stream", iterations=1)

    engine.harness_runner.run = _run_harness
    engine.loop_runner.run_loop_core = _run_loop_core

    await engine.execute("ship")
    events = [event async for event in engine.execute_streaming("ship")]

    assert isinstance(events[0], DoneEvent)
    assert engine.run_lifecycle.prepare.call_count == 2
    assert engine.run_lifecycle.finalize_success.call_count == 2
    assert engine.run_lifecycle.stop.call_count == 2
    assert engine.run_lifecycle.finalize_success.call_args_list[0].args == (prepared, "batch")
    assert engine.run_lifecycle.finalize_success.call_args_list[1].args == (prepared, "stream")
