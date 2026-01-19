"""
Database Skill Loader - 从数据库加载Skills

支持通过数据库动态配置和管理Skills。

数据库Schema:
- skills: 主表（skill_id, name, description, instructions等）
- skill_scripts: 脚本表
- skill_references: 参考资料表
- skill_tools: 工具关联表
"""

from typing import Any

from .loader import SkillLoader
from .models import SkillDefinition


class DatabaseSkillLoader(SkillLoader):
    """
    从数据库加载Skills

    使用原始SQL查询，避免依赖特定ORM。
    """

    def __init__(self, db_connection: Any):
        """
        初始化数据库加载器

        Args:
            db_connection: 数据库连接对象（支持execute方法）
        """
        self.db = db_connection

    async def load_skill(self, skill_id: str) -> SkillDefinition | None:
        """加载单个Skill"""
        # 查询主表
        query = """
            SELECT skill_id, name, description, activation_criteria,
                   instructions, metadata
            FROM skills
            WHERE skill_id = %s
        """
        result = await self._execute_query(query, (skill_id,))
        if not result:
            return None

        skill_data = result[0]

        # 加载scripts
        scripts = await self._load_scripts(skill_id)

        # 加载references
        references = await self._load_references(skill_id)

        # 加载required_tools
        required_tools = await self._load_tools(skill_id)

        return SkillDefinition(
            skill_id=skill_data["skill_id"],
            name=skill_data["name"],
            description=skill_data["description"],
            activation_criteria=skill_data.get("activation_criteria", ""),
            instructions=skill_data["instructions"],
            scripts=scripts,
            references=references,
            required_tools=required_tools,
            metadata=skill_data.get("metadata", {}),
            source="database",
        )

    async def list_skills(self) -> list[SkillDefinition]:
        """列出所有Skills"""
        query = "SELECT skill_id FROM skills"
        results = await self._execute_query(query)

        skills = []
        for row in results:
            skill = await self.load_skill(row["skill_id"])
            if skill:
                skills.append(skill)

        return skills

    async def list_skill_metadata(self) -> list[dict]:
        """列出所有Skills的元数据"""
        query = """
            SELECT skill_id, name, description, activation_criteria
            FROM skills
        """
        results = await self._execute_query(query)

        return [
            {
                "skill_id": row["skill_id"],
                "name": row["name"],
                "description": row["description"],
                "activation_criteria": row.get("activation_criteria", ""),
                "source": "database",
            }
            for row in results
        ]

    async def _load_scripts(self, skill_id: str) -> dict[str, str]:
        """加载Skill的scripts"""
        query = """
            SELECT filename, content
            FROM skill_scripts
            WHERE skill_id = %s
        """
        results = await self._execute_query(query, (skill_id,))
        return {row["filename"]: row["content"] for row in results}

    async def _load_references(self, skill_id: str) -> dict[str, str]:
        """加载Skill的references"""
        query = """
            SELECT filename, content
            FROM skill_references
            WHERE skill_id = %s
        """
        results = await self._execute_query(query, (skill_id,))
        return {row["filename"]: row["content"] for row in results}

    async def _load_tools(self, skill_id: str) -> list[str]:
        """加载Skill需要的tools"""
        query = """
            SELECT tool_name
            FROM skill_tools
            WHERE skill_id = %s
        """
        results = await self._execute_query(query, (skill_id,))
        return [row["tool_name"] for row in results]

    async def _execute_query(self, query: str, params: tuple = ()) -> list[dict]:
        """
        执行SQL查询

        Args:
            query: SQL查询语句
            params: 查询参数

        Returns:
            结果列表（字典格式）
        """
        # 这里需要根据实际的数据库连接实现
        # 示例使用asyncpg或类似库
        try:
            if hasattr(self.db, "fetch"):
                # asyncpg风格
                rows = await self.db.fetch(query, *params)
                return [dict(row) for row in rows]
            elif hasattr(self.db, "execute"):
                # 其他异步库
                cursor = await self.db.execute(query, params)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
            else:
                raise NotImplementedError("Unsupported database connection type")
        except Exception as e:
            print(f"Database query error: {e}")
            return []
