"""
Loom Skills - Agent 技能系统

提供可扩展的技能管理能力，支持：
- 技能创建、编辑、删除
- 三层渐进式披露
- 零侵入集成
- 智能上下文管理
"""

from loom.skills.skill import Skill, SkillMetadata
from loom.skills.manager import SkillManager

__all__ = [
    "Skill",
    "SkillMetadata",
    "SkillManager",
]
