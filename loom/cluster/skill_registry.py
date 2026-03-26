"""SkillNodeRegistry — catalog of available-but-not-loaded skills."""

from __future__ import annotations

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

    @property
    def size(self) -> int:
        return len(self._catalog)
