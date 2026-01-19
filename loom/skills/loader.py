"""
Skill Loader - 统一的Skill加载接口

支持多种数据源：
1. Database
2. Filesystem (SKILL.md)
3. 可扩展到其他来源（HTTP, Git等）
"""

from abc import ABC, abstractmethod

from .models import SkillDefinition


class SkillLoader(ABC):
    """
    Skill加载器抽象基类

    所有Skill加载器必须实现此接口。
    """

    @abstractmethod
    async def load_skill(self, skill_id: str) -> SkillDefinition | None:
        """
        加载单个Skill

        Args:
            skill_id: Skill唯一标识

        Returns:
            SkillDefinition对象，如果不存在返回None
        """
        pass

    @abstractmethod
    async def list_skills(self) -> list[SkillDefinition]:
        """
        列出所有可用的Skills

        Returns:
            SkillDefinition列表
        """
        pass

    @abstractmethod
    async def list_skill_metadata(self) -> list[dict]:
        """
        列出所有Skills的元数据（用于Progressive Disclosure）

        只返回name和description，不加载完整内容。

        Returns:
            元数据字典列表
        """
        pass
