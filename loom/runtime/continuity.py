"""Runtime continuity policies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .task import RuntimeTask

if TYPE_CHECKING:
    from ..context import ContextPartitions
    from ..types.handoff import HandoffArtifact


@dataclass(slots=True)
class ContinuityResult:
    """Result of applying a continuity policy."""

    context: ContextPartitions
    artifact: HandoffArtifact
    metadata: dict[str, Any] = field(default_factory=dict)


class ContinuityPolicy:
    """Factory and base contract for runtime continuity policies."""

    @staticmethod
    def handoff() -> HandoffContinuityPolicy:
        """Use structured handoff continuity across context renewal."""
        return HandoffContinuityPolicy()

    def renew(
        self,
        context: ContextPartitions,
        task: RuntimeTask | str,
        *,
        sprint: int = 0,
    ) -> ContinuityResult:
        raise NotImplementedError


class HandoffContinuityPolicy(ContinuityPolicy):
    """Continuity policy backed by ContextRenewer and HandoffArtifact."""

    def renew(
        self,
        context: ContextPartitions,
        task: RuntimeTask | str,
        *,
        sprint: int = 0,
    ) -> ContinuityResult:
        from ..context.renewal import ContextRenewer

        normalized = RuntimeTask.from_input(task)
        renewed_context, artifact = ContextRenewer().renew(
            context,
            normalized.goal,
            sprint=sprint,
        )
        return ContinuityResult(
            context=renewed_context,
            artifact=artifact,
            metadata={"policy": "handoff"},
        )
