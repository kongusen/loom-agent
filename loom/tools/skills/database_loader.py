"""
Database Skill Loader - 从数据库加载 Skills

提供灵活的数据库加载接口，不依赖具体 ORM 实现。
上层应用可以：
1. 继承 DatabaseSkillLoader 实现自己的查询逻辑
2. 使用 CallbackSkillLoader 传入查询函数
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from .loader import SkillLoader
from .models import SkillDefinition


@dataclass
class BundledTool:
    """
    捆绑的工具定义

    Skill 可以携带工具定义，激活时自动注册。
    """

    name: str
    description: str
    parameters: dict[str, Any]
    implementation: str | None = None  # Python 代码（动态工具）
    source: str = "bundled"


@dataclass
class SkillWithTools:
    """Skill 及其捆绑的工具"""

    skill: SkillDefinition
    tools: list[BundledTool] = field(default_factory=list)


class DatabaseSkillLoader(SkillLoader):
    """
    数据库 Skill 加载器抽象基类

    子类需要实现具体的数据库查询逻辑。
    """

    async def load_skill(self, skill_id: str) -> SkillDefinition | None:
        """加载单个 Skill"""
        result = await self.query_skill(skill_id)
        if result is None:
            return None
        return self._to_skill_definition(result)

    async def list_skills(self) -> list[SkillDefinition]:
        """列出所有 Skills"""
        results = await self.query_all_skills()
        return [self._to_skill_definition(r) for r in results]

    async def list_skill_metadata(self) -> list[dict]:
        """列出所有 Skills 的元数据"""
        return await self.query_skill_metadata()

    # === 子类需要实现的方法 ===

    async def query_skill(self, skill_id: str) -> dict[str, Any] | None:
        """
        查询单个 Skill（子类实现）

        Returns:
            包含 skill_id, name, description, instructions,
            required_tools, references, metadata 的字典
        """
        raise NotImplementedError

    async def query_all_skills(self) -> list[dict[str, Any]]:
        """查询所有 Skills（子类实现）"""
        raise NotImplementedError

    async def query_skill_metadata(self) -> list[dict]:
        """查询所有 Skills 元数据（子类实现）"""
        raise NotImplementedError

    # === 带工具加载（可选实现）===

    async def load_skill_with_tools(self, skill_id: str) -> SkillWithTools | None:
        """
        加载 Skill 及其捆绑的工具

        子类可覆盖此方法实现工具加载。
        默认实现只返回 Skill，不带工具。
        """
        skill = await self.load_skill(skill_id)
        if skill is None:
            return None
        return SkillWithTools(skill=skill, tools=[])

    # === 辅助方法 ===

    def _to_skill_definition(self, data: dict[str, Any]) -> SkillDefinition:
        """将查询结果转换为 SkillDefinition"""
        return SkillDefinition(
            skill_id=data.get("skill_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            instructions=data.get("instructions", ""),
            required_tools=data.get("required_tools", []),
            references=data.get("references", {}),
            metadata=data.get("metadata", {}),
            source="database",
        )


# 回调函数类型定义
QuerySkillFunc = Callable[[str], Awaitable[dict[str, Any] | None]]
QueryAllSkillsFunc = Callable[[], Awaitable[list[dict[str, Any]]]]
QueryMetadataFunc = Callable[[], Awaitable[list[dict]]]


class CallbackSkillLoader(DatabaseSkillLoader):
    """
    基于回调函数的 Skill 加载器

    允许用户传入查询函数，无需继承。

    示例:
        async def my_query(skill_id: str) -> dict | None:
            return await db.fetch_one(
                "SELECT * FROM skills WHERE skill_id = $1",
                skill_id
            )

        loader = CallbackSkillLoader(
            query_skill_fn=my_query,
            query_all_fn=...,
            query_metadata_fn=...,
        )
    """

    def __init__(
        self,
        query_skill_fn: QuerySkillFunc,
        query_all_fn: QueryAllSkillsFunc | None = None,
        query_metadata_fn: QueryMetadataFunc | None = None,
    ):
        self._query_skill_fn = query_skill_fn
        self._query_all_fn = query_all_fn
        self._query_metadata_fn = query_metadata_fn

    async def query_skill(self, skill_id: str) -> dict[str, Any] | None:
        """调用查询函数"""
        return await self._query_skill_fn(skill_id)

    async def query_all_skills(self) -> list[dict[str, Any]]:
        """调用查询所有函数"""
        if self._query_all_fn is None:
            return []
        return await self._query_all_fn()

    async def query_skill_metadata(self) -> list[dict]:
        """调用元数据查询函数"""
        if self._query_metadata_fn is None:
            # 降级：从完整查询中提取元数据
            skills = await self.query_all_skills()
            return [
                {
                    "skill_id": s.get("skill_id"),
                    "name": s.get("name"),
                    "description": s.get("description"),
                    "source": "database",
                }
                for s in skills
            ]
        return await self._query_metadata_fn()
