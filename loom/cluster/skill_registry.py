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

    @property
    def size(self) -> int:
        return len(self._catalog)

    async def find_match(self, input_text: str, min_score: float = 0.3):
        for skill in self._catalog.values():
            if skill.name in self._loaded:
                continue
            trigger = getattr(skill, "trigger", None)
            if not trigger:
                continue
            if trigger.get("type") == "keyword":
                lower = input_text.lower()
                matched = [k for k in trigger.get("keywords", []) if k.lower() in lower]
                if matched:
                    score = (getattr(skill, "priority", 0.5)) * (len(matched) / len(trigger["keywords"]))
                    if score >= min_score:
                        return {"skill": skill, "score": score, "reason": f"keywords: {', '.join(matched)}"}
        return None
