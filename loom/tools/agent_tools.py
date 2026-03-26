"""E1/E2 工具实现"""

from ..types import ToolDefinition


def create_memory_tools() -> list[ToolDefinition]:
    """创建记忆管理工具（E1）"""
    return [
        ToolDefinition(
            name="write_memory",
            description="Write important information to long-term memory",
            input_schema={
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
            },
        )
    ]


def create_skill_tools() -> list[ToolDefinition]:
    """创建技能管理工具（E2）"""
    return [
        ToolDefinition(
            name="activate_skill",
            description="Activate a skill to use its capabilities",
            input_schema={
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "Name of skill to activate"}
                },
                "required": ["skill_name"],
            },
        ),
        ToolDefinition(
            name="deactivate_skill",
            description="Deactivate a skill to free up context budget",
            input_schema={
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "Name of skill to deactivate"}
                },
                "required": ["skill_name"],
            },
        ),
    ]
