"""SkillCatalogProvider — LLM semantic routing for progressive skill loading."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from ..types import CompletionParams, ContextFragment, ContextSource, UserMessage

if TYPE_CHECKING:
    from ..cluster.skill_registry import SkillNodeRegistry
    from ..types import LLMProvider
    from .registry import SkillRegistry


class SkillCatalogProvider:
    """ContextProvider that uses LLM to discover and load skills on demand.

    Implements the Progressive Disclosure pattern:
      Level 1 — describe_all() summaries fed to LLM
      Level 2 — LLM selects best skill → loaded into SkillRegistry
      Level 3 — SkillProvider handles execution context
    """

    source = ContextSource.SKILL

    def __init__(
        self,
        catalog: SkillNodeRegistry,
        registry: SkillRegistry,
        llm: LLMProvider,
    ) -> None:
        self._catalog = catalog
        self._registry = registry
        self._llm = llm

    async def provide(self, query: str, budget: int) -> list[ContextFragment]:
        descs = [d for d in self._catalog.describe_all() if not self._catalog.is_loaded(d["name"])]
        if not descs:
            return []

        name = await self._select(query, descs)
        if not name:
            return []

        skill = self._catalog.get(name)
        if not skill:
            return []

        # Load into SkillRegistry (Level 2 activation)
        self._registry.register(skill)
        self._catalog.mark_loaded(name)

        instructions = getattr(skill, "instructions", "")
        if not instructions:
            return []

        tokens = len(instructions) // 4 + 1
        if tokens > budget:
            return []

        return [
            ContextFragment(
                source=ContextSource.SKILL,
                content=instructions,
                tokens=tokens,
                relevance=0.9,
                metadata={"skill_name": name, "reason": "llm_semantic_route"},
            )
        ]

    async def _select(self, query: str, skills: list[dict[str, str]]) -> str | None:
        listing = "\n".join(f"- {s['name']}: {s['description']}" for s in skills)
        try:
            r = await self._llm.complete(
                CompletionParams(
                    messages=[
                        UserMessage(
                            content=(
                                "You are a skill router. Given a task and available skills, "
                                "pick the BEST matching skill or reply null.\n\n"
                                f"Skills:\n{listing}\n\n"
                                'Reply ONLY JSON: {{"skill":"<name>"}}\n'
                                "If none match, reply: null\n\n"
                                f"Task: {query}"
                            )
                        )
                    ],
                    temperature=0,
                    max_tokens=64,
                )
            )
            m = re.search(r"\{[\s\S]*?\}", r.content)
            if not m:
                return None
            obj = json.loads(m.group())
            picked = obj.get("skill", "")
            valid = {s["name"] for s in skills}
            return picked if picked in valid else None
        except Exception:
            return None
