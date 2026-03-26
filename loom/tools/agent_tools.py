"""E1/E2 工具实现"""

from typing import Any

from ..types import ToolDefinition
from .schema import DictSchema


def create_memory_tools(agent: Any) -> list[ToolDefinition]:
    """创建记忆管理工具（E1）"""
    from ..agent.evolution_handlers import write_memory_handler

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
            execute=lambda params, ctx: write_memory_handler(params, ctx, agent),
        )
    ]


def create_skill_tools(agent: Any) -> list[ToolDefinition]:
    """创建技能管理工具（E2）"""
    from ..agent.evolution_handlers import activate_skill_handler, deactivate_skill_handler

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
            execute=lambda params, ctx: activate_skill_handler(params, ctx, agent),
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
            execute=lambda params, ctx: deactivate_skill_handler(params, ctx, agent),
        ),
    ]
