"""
Skill Registry - 统一的Skill管理中心

负责：
1. 管理多个SkillLoader
2. 统一访问所有Skills
3. Progressive Disclosure（渐进式加载）
"""

from .loader import SkillLoader
from .models import SkillDefinition


class SkillRegistry:
    """
    Skill注册表

    支持多个Loader，统一管理来自不同来源的Skills。
    """

    def __init__(self):
        """初始化Skill注册表"""
        self.loaders: list[SkillLoader] = []
        self._metadata_cache: list[dict] | None = None
        self._skills_cache: dict[str, SkillDefinition] | None = None

    def register_loader(self, loader: SkillLoader) -> None:
        """
        注册Skill加载器

        Args:
            loader: SkillLoader实例
        """
        self.loaders.append(loader)
        # 清除缓存
        self._metadata_cache = None
        self._skills_cache = None

    async def get_skill(self, skill_id: str) -> SkillDefinition | None:
        """
        获取单个Skill

        Args:
            skill_id: Skill唯一标识

        Returns:
            SkillDefinition对象，如果不存在返回None
        """
        # 尝试从缓存获取
        if self._skills_cache and skill_id in self._skills_cache:
            return self._skills_cache[skill_id]

        # 从所有Loader中查找
        for loader in self.loaders:
            skill = await loader.load_skill(skill_id)
            if skill:
                # 更新缓存
                if self._skills_cache is None:
                    self._skills_cache = {}
                self._skills_cache[skill_id] = skill
                return skill

        return None

    async def get_all_skills(self) -> list[SkillDefinition]:
        """
        获取所有Skills（完整加载）

        Returns:
            SkillDefinition列表
        """
        skills = []
        for loader in self.loaders:
            loader_skills = await loader.list_skills()
            skills.extend(loader_skills)

        # 更新缓存
        self._skills_cache = {skill.skill_id: skill for skill in skills}

        return skills

    async def get_all_metadata(self) -> list[dict]:
        """
        获取所有Skills的元数据（Progressive Disclosure第一阶段）

        只加载name和description，不加载完整内容。

        Returns:
            元数据字典列表
        """
        if self._metadata_cache is not None:
            return self._metadata_cache

        metadata_list = []
        for loader in self.loaders:
            loader_metadata = await loader.list_skill_metadata()
            metadata_list.extend(loader_metadata)

        self._metadata_cache = metadata_list
        return metadata_list

    def clear_cache(self) -> None:
        """清除缓存"""
        self._metadata_cache = None
        self._skills_cache = None
