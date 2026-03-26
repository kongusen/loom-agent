"""SkillNodeRegistry — catalog of available-but-not-loaded skills."""

from __future__ import annotations

import re
from typing import Any


class SkillNodeRegistry:
    def __init__(self) -> None:
        self._catalog: dict[str, Any] = {}
        self._loaded: set[str] = set()

    def register(self, skill) -> None:
        self._catalog[skill.name] = skill

    def register_all(self, skills: list) -> None:
        for s in skills:
            self.register(s)

    def mark_loaded(self, name: str) -> None:
        self._loaded.add(name)

    def is_loaded(self, name: str) -> bool:
        return name in self._loaded

    def get(self, name: str):
        return self._catalog.get(name)

    def describe_all(self) -> list[dict[str, str]]:
        """Return name+description of ALL skills (for LLM semantic matching)."""
        return [
            {"name": s.name, "description": getattr(s, "description", s.name)}
            for s in self._catalog.values()
        ]

    async def find_match(self, input_text: str) -> dict[str, Any] | None:
        """Best-effort local skill discovery for runtimes without LLM routing."""
        terms = {token for token in re.findall(r"[a-z0-9]+", input_text.lower()) if len(token) >= 2}
        if not terms:
            return None

        best_skill: Any | None = None
        best_score = 0
        for skill in self._catalog.values():
            if skill.name in self._loaded:
                continue
            haystack = " ".join(
                [
                    getattr(skill, "name", ""),
                    getattr(skill, "description", ""),
                ]
            ).lower()
            score = sum(1 for term in terms if term in haystack)
            if score > best_score:
                best_skill = skill
                best_score = score

        if best_skill is None:
            return None
        return {"skill": best_skill, "score": float(best_score)}

    @property
    def size(self) -> int:
        return len(self._catalog)
