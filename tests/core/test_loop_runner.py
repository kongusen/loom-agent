"""Tests for the explicit LoopRunner service boundary."""

from unittest.mock import MagicMock

from loom.runtime.engine import AgentEngine, EngineConfig


def test_loop_runner_uses_runtime_services_boundary() -> None:
    engine = AgentEngine(provider=MagicMock(), config=EngineConfig())

    assert not hasattr(engine.loop_runner, "engine")
    assert engine.loop_runner.services.context_manager is engine.context_manager
    assert engine.loop_runner.services.memory_runtime is engine.memory_runtime


def test_loop_runner_services_track_reassigned_context_manager() -> None:
    engine = AgentEngine(provider=MagicMock(), config=EngineConfig())
    replacement_context = MagicMock()

    engine.context_manager = replacement_context
    engine._refresh_runtime_wiring()

    assert engine.loop_runner.services.context_manager is replacement_context
