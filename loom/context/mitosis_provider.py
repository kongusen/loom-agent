"""MitosisContextProvider — injects parent task context during agent splitting."""

from __future__ import annotations

from ..types import ContextFragment, ContextSource, MitosisContext


class MitosisContextProvider:
    """Injects parent task objective, subtask description, and parent tools into child context."""

    source = ContextSource.MITOSIS

    def __init__(self, mitosis_ctx: MitosisContext) -> None:
        self._ctx = mitosis_ctx

    async def provide(self, query: str, budget: int) -> list[ContextFragment]:
        parts = []
        if self._ctx.parent_task_spec and self._ctx.parent_task_spec.objective:
            parts.append(f"Parent objective: {self._ctx.parent_task_spec.objective}")
        if self._ctx.subtask:
            parts.append(f"Subtask: {self._ctx.subtask.description}")
        if self._ctx.parent_tools:
            parts.append(f"Available tools: {', '.join(self._ctx.parent_tools)}")
        if not parts:
            return []
        content = "\n".join(parts)
        tokens = len(content.split()) * 2
        if tokens > budget:
            content = content[:budget * 2]
            tokens = budget
        return [ContextFragment(
            source=ContextSource.MITOSIS,
            content=content,
            tokens=tokens,
            relevance=0.9,
        )]
