"""Tests for runtime context policy adapters."""

from loom import (
    Agent,
    ContextMetrics,
    ContextPolicy,
    ContextProtocol,
    ContextSnapshot,
    Model,
    Runtime,
)
from loom.context import ContextManager, ContextPartitions
from loom.runtime import RuntimeTask
from loom.types import Message


def test_context_policy_is_context_protocol() -> None:
    """ContextProtocol is a backward-compatible alias for ContextPolicy."""
    assert ContextProtocol is ContextPolicy


def test_context_policy_manager_renders_task_goal() -> None:
    context = ContextPolicy.manager(max_tokens=10_000)
    context.partitions.system.append(Message(role="system", content="system rules"))

    messages = context.render(RuntimeTask(goal="build context protocol"))

    assert messages[0].content == "system rules"
    assert messages[-1].role == "user"
    assert messages[-1].content == "build context protocol"


def test_context_policy_measures_and_snapshots_context() -> None:
    context = ContextPolicy.manager(max_tokens=10_000)
    context.partitions.history.append(Message(role="assistant", content="done"))

    metrics = context.measure()
    snapshot = context.snapshot(metadata={"source": "test"})

    assert isinstance(metrics, ContextMetrics)
    assert metrics.token_count > 0
    assert metrics.max_tokens == 10_000
    assert isinstance(snapshot, ContextSnapshot)
    assert snapshot.partitions is context.partitions
    assert snapshot.metadata == {"source": "test"}


def test_context_policy_compact_and_renew_wrap_existing_manager() -> None:
    manager = ContextManager(max_tokens=10_000)
    manager.partitions.working.goal_progress = "Implemented protocol"
    manager.partitions.working.plan = ["wire engine"]
    manager.partitions.history.extend(
        Message(role="user", content=f"message {idx}") for idx in range(20)
    )

    context = ContextPolicy.from_manager(manager)
    compacted = context.compact("snip")
    renewed = context.renew("finish runtime context")

    assert compacted.metadata == {"operation": "compact", "strategy": "snip"}
    assert renewed.metadata == {"operation": "renew"}
    assert renewed.handoff is not None
    assert renewed.handoff.goal == "finish runtime context"
    assert context.partitions.working.goal_progress == "Implemented protocol"
    assert context.partitions.working.plan == ["wire engine"]


def test_agent_runtime_accepts_context_policy() -> None:
    from loom.providers.base import CompletionRequest, CompletionResponse, LLMProvider

    class MockProvider(LLMProvider):
        async def _complete_request(self, request: CompletionRequest) -> CompletionResponse:
            return CompletionResponse(content="ok")

    context = ContextPolicy.manager(max_tokens=12_345)
    agent = Agent(
        model=Model.openai("gpt-test"),
        runtime=Runtime(context=context),
    )

    engine = agent._build_engine(MockProvider())

    assert agent.config.runtime.context is context
    assert engine.context_protocol is context
    assert engine.context_manager is context
    assert engine.context_manager.measure().max_tokens == 12_345


def test_context_metrics_utilization_alias() -> None:
    context = ContextPolicy.manager(max_tokens=10_000)
    context.partitions.history.append(Message(role="assistant", content="done"))
    metrics = context.measure()
    assert metrics.utilization == metrics.rho


def test_context_policy_keeps_context_partitions_shape() -> None:
    context = ContextPolicy.manager()

    assert isinstance(context.partitions, ContextPartitions)
    assert context.snapshot().partitions.get_all_messages()
