"""Skill Tool - 让 Agent 动态加载技能的完整 instructions"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from ..types import ToolContext, ToolDefinition
from .schema import PydanticSchema

if TYPE_CHECKING:
    from ..skills import SkillRegistry


class SkillParams(BaseModel):
    name: str


def create_skill_tool(registry: SkillRegistry) -> ToolDefinition:
    """创建 Skill tool，用于 Progressive Disclosure"""

    async def skill_execute(params: SkillParams, _ctx: ToolContext) -> str:
        """加载指定技能的完整 instructions"""
        instructions = registry.load_skill(params.name)
        if instructions is None:
            available = [s.name for s in registry.all()]
            return f"Skill '{params.name}' not found. Available: {', '.join(available)}"
        return instructions

    return ToolDefinition(
        name="Skill",
        description="Load full instructions for a specific skill. Use when you need detailed guidance.",
        parameters=PydanticSchema(SkillParams),
        execute=skill_execute,
    )
