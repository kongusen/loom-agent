"""SkillProvider — bridges skills into context orchestrator."""

from __future__ import annotations

from ..types import ContextFragment, ContextSource
from .registry import SkillRegistry


class SkillProvider:
    source = ContextSource.SKILL

    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry

    async def provide(self, query: str, budget: int) -> list[ContextFragment]:
        activations = await self._registry.activate(query)
        frags: list[ContextFragment] = []
        used = 0
        for act in activations:
            # Amoba pattern: skill.provideContext() takes priority over instructions
            if hasattr(act.skill, "provide_context") and callable(act.skill.provide_context):
                try:
                    custom_frags = await act.skill.provide_context(query, budget - used)
                    for f in custom_frags or []:
                        if used + f.tokens > budget:
                            break
                        frags.append(f)
                        used += f.tokens
                    continue
                except Exception:
                    pass  # fall through to instructions
            instructions = getattr(act.skill, "instructions", "")
            if not instructions:
                continue
            tokens = len(instructions) // 4 + 1
            if used + tokens > budget:
                continue
            frags.append(
                ContextFragment(
                    source=ContextSource.SKILL,
                    content=instructions,
                    tokens=tokens,
                    relevance=act.score,
                    metadata={"skill_name": act.skill.name, "reason": act.reason},
                )
            )
            used += tokens
        return frags
