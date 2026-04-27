"""Runtime context protocol and adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from typing import Protocol as TypingProtocol

from ..context import CompressionPolicy, ContextManager, ContextPartitions
from ..types import Message
from ..types.handoff import HandoffArtifact
from ..utils import count_messages_tokens
from .task import RuntimeTask

if TYPE_CHECKING:
    from ..context.dashboard import DashboardManager
    from .signals import RuntimeSignal, SignalDecision


@dataclass(slots=True)
class ContextMetrics:
    """Measured state of a runtime context."""

    rho: float
    token_count: int
    max_tokens: int
    should_renew: bool
    compression_strategy: str | None = None


@dataclass(slots=True)
class ContextSnapshot:
    """Point-in-time view of the runtime context."""

    partitions: ContextPartitions
    metrics: ContextMetrics
    handoff: HandoffArtifact | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class RuntimeContextProtocol(TypingProtocol):
    """Protocol implemented by runtime context engines."""

    partitions: ContextPartitions
    current_goal: str

    @property
    def last_handoff(self) -> HandoffArtifact | None: ...

    def render(self, task: RuntimeTask | str | None = None) -> list[Message]: ...

    def measure(self) -> ContextMetrics: ...

    def should_renew(self) -> bool: ...

    def should_compress(self) -> str | None: ...

    def compact(self, strategy: str) -> ContextSnapshot: ...

    def renew(self, task: RuntimeTask | str | None = None) -> ContextSnapshot: ...

    def snapshot(self) -> ContextSnapshot: ...

    def ingest_signal(
        self,
        signal: RuntimeSignal,
        decision: SignalDecision | None = None,
    ) -> None: ...


class ContextProtocol:
    """Factory for built-in runtime context protocol implementations."""

    @staticmethod
    def manager(
        *,
        max_tokens: int = 200000,
        compression_policy: CompressionPolicy | None = None,
        continuity: Any | None = None,
    ) -> ManagedContextProtocol:
        manager = ContextManager(
            max_tokens=max_tokens,
            compression_policy=compression_policy,
            continuity_policy=continuity,
        )
        return ManagedContextProtocol(manager)

    @staticmethod
    def from_manager(manager: ContextManager) -> ManagedContextProtocol:
        return ManagedContextProtocol(manager)


class ManagedContextProtocol:
    """Runtime context adapter backed by the existing ContextManager."""

    def __init__(self, manager: ContextManager) -> None:
        self.manager = manager

    def __getattr__(self, name: str) -> Any:
        return getattr(self.manager, name)

    @property
    def partitions(self) -> ContextPartitions:
        return self.manager.partitions

    @partitions.setter
    def partitions(self, value: ContextPartitions) -> None:
        self.manager.partitions = value

    @property
    def dashboard(self) -> DashboardManager:
        return self.manager.dashboard

    @property
    def current_goal(self) -> str:
        return self.manager.current_goal

    @current_goal.setter
    def current_goal(self, value: str) -> None:
        self.manager.current_goal = value

    @property
    def last_handoff(self) -> HandoffArtifact | None:
        return self.manager.last_handoff

    @property
    def rho(self) -> float:
        return self.manager.rho

    def render(self, task: RuntimeTask | str | None = None) -> list[Message]:
        normalized = RuntimeTask.from_input(task) if task is not None else None
        messages = self.manager.partitions.get_all_messages()
        if normalized is not None and (not messages or messages[-1].role != "user"):
            messages.append(Message(role="user", content=normalized.goal))
        return messages

    def measure(self) -> ContextMetrics:
        token_count = count_messages_tokens(self.manager.partitions.get_all_messages())
        rho = token_count / self.manager.max_tokens
        return ContextMetrics(
            rho=rho,
            token_count=token_count,
            max_tokens=self.manager.max_tokens,
            should_renew=rho >= 1.0,
            compression_strategy=self.manager.compressor.should_compress(rho),
        )

    def should_renew(self) -> bool:
        return self.manager.should_renew()

    def should_compress(self) -> str | None:
        return self.manager.should_compress()

    def compact(self, strategy: str) -> ContextSnapshot:
        self.manager.compress(strategy)
        return self.snapshot(metadata={"operation": "compact", "strategy": strategy})

    def compress(self, strategy: str) -> ContextSnapshot:
        return self.compact(strategy)

    def renew(self, task: RuntimeTask | str | None = None) -> ContextSnapshot:
        if task is not None:
            self.manager.current_goal = RuntimeTask.from_input(task).goal
        self.manager.renew()
        return self.snapshot(metadata={"operation": "renew"})

    def snapshot(self, *, metadata: dict[str, Any] | None = None) -> ContextSnapshot:
        return ContextSnapshot(
            partitions=self.manager.partitions,
            metrics=self.measure(),
            handoff=self.manager.last_handoff,
            metadata=dict(metadata or {}),
        )

    def ingest_signal(
        self,
        signal: RuntimeSignal,
        decision: SignalDecision | None = None,
    ) -> None:
        self.manager.ingest_signal(signal, decision)
