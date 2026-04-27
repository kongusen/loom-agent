"""Runtime task contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RuntimeTask:
    """A normalized unit of work for the runtime."""

    goal: str
    input: dict[str, Any] = field(default_factory=dict)
    criteria: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_input(cls, task: RuntimeTask | str) -> RuntimeTask:
        """Normalize a public run input into a RuntimeTask."""
        if isinstance(task, RuntimeTask):
            return task
        if not isinstance(task, str):
            raise TypeError(f"task must be RuntimeTask or str, got {type(task).__name__}")
        return cls(goal=task)

    def to_context_payload(self) -> dict[str, Any]:
        """Return context fields that should accompany this task."""
        payload = dict(self.input)
        if self.criteria:
            payload["criteria"] = list(self.criteria)
        if self.metadata:
            payload["task_metadata"] = dict(self.metadata)
        return payload
