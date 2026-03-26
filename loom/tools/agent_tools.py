"""E1/E2 工具实现"""

from typing import Any

from .schema import DictSchema
from ..types import ToolDefinition


async def _not_implemented(_params: Any, _ctx: Any) -> str:
    """Placeholder executor until these helpers are wired into Agent handlers."""
    return "Tool factory created a definition, but no executor is wired for this runtime."


def create_memory_tools() -> list[ToolDefinition]:
    """创建记忆管理工具（E1）"""
    return [
        ToolDefinition(
            name="write_memory",
            description="Write important information to long-term memory",
            parameters=DictSchema(
                {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Content to remember"},
                        "importance": {
                            "type": "number",
                            "description": "Importance score (0-1)",
                            "default": 0.7,
                        },
                    },
                    "required": ["content"],
                }
            ),
            execute=_not_implemented,
        )
    ]


def create_skill_tools() -> list[ToolDefinition]:
    """创建技能管理工具（E2）"""
    return [
        ToolDefinition(
            name="activate_skill",
            description="Activate a skill to use its capabilities",
            parameters=DictSchema(
                {
                    "type": "object",
                    "properties": {
                        "skill_name": {
                            "type": "string",
                            "description": "Name of skill to activate",
                        }
                    },
                    "required": ["skill_name"],
                }
            ),
            execute=_not_implemented,
        ),
        ToolDefinition(
            name="deactivate_skill",
            description="Deactivate a skill to free up context budget",
            parameters=DictSchema(
                {
                    "type": "object",
                    "properties": {
                        "skill_name": {
                            "type": "string",
                            "description": "Name of skill to deactivate",
                        }
                    },
                    "required": ["skill_name"],
                }
            ),
            execute=_not_implemented,
        ),
    ]
