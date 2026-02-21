"""SkillRegistry — register, activate, and manage skills."""

from __future__ import annotations

from typing import Any

from ..types import SkillActivation
from .activator import match_trigger


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Any] = {}
        self._active: set[str] = set()

    def register(self, skill: Any) -> None:
        self._skills[skill.name] = skill
        if getattr(skill, "activation_level", None) == "always":
            self._active.add(skill.name)

    def get(self, name: str) -> Any | None:
        return self._skills.get(name)

    def all(self) -> list[Any]:
        return list(self._skills.values())

    def get_active(self) -> list[Any]:
        return [self._skills[n] for n in self._active if n in self._skills]

    async def deactivate(self, name: str) -> None:
        if name in self._active:
            skill = self._skills.get(name)
            if skill and hasattr(skill, "on_deactivate"):
                await skill.on_deactivate()
            self._active.discard(name)

    async def activate(self, input_text: str) -> list[SkillActivation]:
        results: list[SkillActivation] = []
        for skill in self._skills.values():
            level = getattr(skill, "activation_level", "auto")
            if level == "always":
                results.append(SkillActivation(skill=skill, score=1.0, reason="always active"))
                continue
            if level == "on-demand":
                continue
            match = match_trigger(skill, input_text)
            if match:
                if skill.name not in self._active:
                    if hasattr(skill, "on_activate"):
                        await skill.on_activate()
                    self._active.add(skill.name)
                results.append(match)
        results.sort(key=lambda a: a.score, reverse=True)
        return results
