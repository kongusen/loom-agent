"""SkillProvider — bridges skills into context orchestrator."""

from __future__ import annotations

from ..types import ContextFragment, ContextSource
from .registry import SkillRegistry


class SkillProvider:
    source = ContextSource.SKILL

    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry

    async def provide(self, query: str, budget: int) -> list[ContextFragment]:
        # Get active skills (already loaded with instructions)
        active_skills = self._registry.list_active()
        frags: list[ContextFragment] = []
        used = 0

        for skill in active_skills:
            # Amoba pattern: skill.provideContext() takes priority over instructions
            if hasattr(skill, "provide_context") and callable(skill.provide_context):
                try:
                    custom_frags = await skill.provide_context(query, budget - used)
                    for f in custom_frags or []:
                        if used + f.tokens > budget:
                            break
                        frags.append(f)
                        used += f.tokens
                    continue
                except Exception:
                    pass  # fall through to instructions

            instructions = getattr(skill, "instructions", "")
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
                    relevance=0.9,
                    metadata={"skill_name": skill.name},
                )
            )
            used += tokens
        return frags
