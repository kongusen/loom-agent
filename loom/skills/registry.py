"""SkillRegistry — register and manage skills (Claude standard aligned)."""

from __future__ import annotations

from typing import Any


class SkillRegistry:
    def __init__(self) -> None:
        self._catalog: dict[str, Any] = {}  # All available skills (metadata only)
        self._active: dict[str, Any] = {}   # Activated skills (full instructions loaded)

    def register(self, skill: Any) -> None:
        """Register skill to catalog (Layer 1 - Discovery)"""
        self._catalog[skill.name] = skill

    def activate(self, name: str) -> Any | None:
        """Activate skill by loading full instructions (Layer 2 - Activation)"""
        skill = self._catalog.get(name)
        if not skill:
            return None
        skill.load_instructions()
        self._active[name] = skill
        return skill

    def get(self, name: str) -> Any | None:
        return self._catalog.get(name)

    def all(self) -> list[Any]:
        return list(self._catalog.values())



    def invalidate_cache(self) -> None:
        """Clear active skills cache"""
        self._active.clear()

    def get_discovery_prompt(self) -> str:
        """返回轻量级的技能列表（只有 name + description），用于 Layer 1 Discovery"""
        lines = ["<available_skills>"]
        for skill in self._catalog.values():
            name = skill.name
            desc = getattr(skill, "description", "")
            lines.append("  <skill>")
            lines.append(f"    <name>{name}</name>")
            lines.append(f"    <description>{desc}</description>")
            lines.append("  </skill>")
        lines.append("</available_skills>")
        return "\n".join(lines)

    def load_skill(self, name: str) -> str | None:
        """加载技能的完整 instructions（Layer 2 Activation）"""
        skill = self.activate(name)
        if not skill:
            return None
        instructions = getattr(skill, "instructions", "")
        if not instructions:
            return f"Skill '{name}' has no instructions."
        return instructions
