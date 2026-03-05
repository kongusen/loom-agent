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

    def get_discovery_prompt(self) -> str:
        """返回轻量级的技能列表（只有 name + description），用于 discovery 阶段"""
        lines = ["<available_skills>"]
        for skill in self._skills.values():
            name = skill.name
            desc = getattr(skill, "description", "")
            lines.append(f"  <skill>")
            lines.append(f"    <name>{name}</name>")
            lines.append(f"    <description>{desc}</description>")
            lines.append(f"  </skill>")
        lines.append("</available_skills>")
        return "\n".join(lines)

    def load_skill(self, name: str) -> str | None:
        """加载技能的完整 instructions（activation 阶段）"""
        skill = self._skills.get(name)
        if not skill:
            return None
        instructions = getattr(skill, "instructions", "")
        if not instructions:
            return f"Skill '{name}' has no instructions."
        return instructions

    def activate_by_names(self, skill_names: list[str]) -> list[SkillActivation]:
        """根据技能名称列表激活技能（可选，用于显式标记）"""
        results: list[SkillActivation] = []
        for name in skill_names:
            skill = self._skills.get(name)
            if skill:
                if skill.name not in self._active:
                    self._active.add(skill.name)
                results.append(SkillActivation(skill=skill, score=1.0, reason="agent-selected"))
        return results

    async def deactivate(self, name: str) -> None:
        if name in self._active:
            skill = self._skills.get(name)
            if skill and hasattr(skill, "on_deactivate"):
                await skill.on_deactivate()
            self._active.discard(name)
