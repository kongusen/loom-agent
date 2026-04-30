"""Tests for runtime signal coordination extraction."""

from unittest.mock import MagicMock

from loom.runtime.engine import AgentEngine, EngineConfig
from loom.runtime.signal_runtime import SignalRuntime
from loom.runtime.signals import AttentionPolicy, RuntimeSignal, SignalQueue


class _Dashboard:
    def decision_state(self):
        return {}


class _ContextManager:
    def __init__(self) -> None:
        self.dashboard = _Dashboard()
        self.ingested: list[tuple[RuntimeSignal, object]] = []

    def ingest_signal(self, signal, decision) -> None:
        self.ingested.append((signal, decision))


def test_signal_runtime_ingest_emits_received_and_decided() -> None:
    events: list[tuple[str, dict]] = []
    runtime = SignalRuntime(
        context_manager=_ContextManager(),
        emit=lambda name, **payload: events.append((name, payload)),
    )

    decision = runtime.ingest_signal("new issue reported", source="gateway")

    assert decision.action in {"run", "observe", "queue", "interrupt"}
    assert [name for name, _ in events] == ["signal_received", "signal_decided"]


def test_signal_runtime_drain_dispatches_into_context() -> None:
    context_manager = _ContextManager()
    events: list[str] = []
    runtime = SignalRuntime(
        context_manager=context_manager,
        emit=lambda name, **_: events.append(name),
    )
    runtime.ingest_signal("deploy health check", source="heartbeat")

    drained = runtime.drain_signals()

    assert len(drained) == 1
    assert len(context_manager.ingested) == 1
    assert "signal_dispatched" in events


def test_signal_runtime_heartbeat_handler_enqueues_signal() -> None:
    runtime = SignalRuntime(
        context_manager=_ContextManager(),
        emit=lambda _name, **_kwargs: None,
    )

    runtime.handle_heartbeat_event({"type": "resource", "event_id": "hb-1"}, "high")
    drained = runtime.drain_signals()

    assert len(drained) == 1
    signal, _decision = drained[0]
    assert signal.source == "heartbeat"
    assert signal.type == "resource"
    assert signal.dedupe_key == "hb-1"


def test_agent_engine_signal_runtime_accepts_queue_and_policy_rebinding() -> None:
    engine = AgentEngine(provider=MagicMock(), config=EngineConfig())
    queue = SignalQueue()
    policy = AttentionPolicy()

    engine.signal_runtime.signal_queue = queue
    engine.signal_runtime.attention_policy = policy

    assert engine.signal_runtime.signal_queue is queue
    assert engine.signal_runtime.attention_policy is policy

    engine.ingest_signal("queued through signal runtime")

    drained = queue.drain()
    assert len(drained) == 1
    assert drained[0].summary == "queued through signal runtime"


def test_agent_engine_signal_runtime_tracks_reassigned_context_manager() -> None:
    engine = AgentEngine(provider=MagicMock(), config=EngineConfig())
    replacement_context = _ContextManager()

    engine.context_manager = replacement_context
    engine.ingest_signal("uses replacement context")
    engine._refresh_runtime_wiring()
    engine.signal_runtime.drain_signals()

    assert len(replacement_context.ingested) == 1
    assert replacement_context.ingested[0][0].summary == "uses replacement context"
