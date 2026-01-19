"""
Skill Registry - Skills 市场

Skills 是工具，不是节点。
Skills 市场提供工具定义的注册、发现和加载。

设计原则：
1. Skill = Tool - 不是节点
2. 支持三种来源：Python、MCP、HTTP
3. 简单的注册和发现机制
"""

from collections.abc import Callable
from typing import Any


class SkillRegistry:
    """
    Skills 注册表

    管理用户创建的 Skills（工具）。
    """

    def __init__(self):
        """初始化 Skills 注册表"""
        self._skills: dict[str, dict[str, Any]] = {}

    def register_skill(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: Callable,
        source: str = "python",
        ephemeral: int = 0,
        **metadata: Any,
    ) -> dict[str, Any]:
        """
        注册一个 Skill

        Args:
            name: Skill 名称
            description: Skill 描述
            parameters: 参数定义（OpenAI 格式）
            handler: 处理函数
            source: 来源类型（python/mcp/http）
            ephemeral: 是否是 ephemeral 工具
            **metadata: 其他元数据

        Returns:
            工具定义字典
        """
        skill_def = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
            "_handler": handler,
            "_source": source,
            "_ephemeral": ephemeral,
            "_metadata": metadata,
        }

        self._skills[name] = skill_def
        return skill_def

    def get_skill(self, name: str) -> dict[str, Any] | None:
        """获取 Skill 定义"""
        return self._skills.get(name)

    def list_skills(self) -> list[str]:
        """列出所有 Skill 名称"""
        return list(self._skills.keys())

    def get_skills_by_source(self, source: str) -> list[dict[str, Any]]:
        """按来源类型获取 Skills"""
        return [skill for skill in self._skills.values() if skill.get("_source") == source]


# 全局 Skills 市场实例
skill_market = SkillRegistry()
