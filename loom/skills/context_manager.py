"""SkillContextManager — 技能加载与预算管理（公理一）"""

from __future__ import annotations

from ..types import Skill, Tokenizer
from .registry import SkillRegistry


class SkillContextManager:
    """管理 C_skill 分区，集成渐进式加载"""

    def __init__(self, registry: SkillRegistry, tokenizer: Tokenizer):
        self.registry = registry
        self.tokenizer = tokenizer
        self.active_skills: dict[str, Skill] = {}

    def get_discovery_prompt(self) -> str:
        """Layer 1: 轻量级发现提示（只有 name + description）"""
        return self.registry.get_discovery_prompt()

    def activate(self, name: str, budget: int) -> bool:
        """Layer 2: 激活技能，检查预算"""
        skill = self.registry.activate(name)
        if not skill or not skill.instructions:
            return False

        tokens = self.tokenizer.count(skill.instructions)
        current_usage = sum(
            self.tokenizer.count(s.instructions) for s in self.active_skills.values()
        )

        if current_usage + tokens > budget:
            return False

        self.active_skills[name] = skill
        return True

    def deactivate(self, name: str) -> None:
        """卸载技能，释放预算"""
        self.active_skills.pop(name, None)

    def get_context(self) -> str:
        """获取当前激活技能的完整上下文"""
        return "\n\n".join(s.instructions for s in self.active_skills.values())

    def compute_tokens(self) -> int:
        """计算 C_skill 当前占用的 token 数"""
        return sum(self.tokenizer.count(s.instructions) for s in self.active_skills.values())
