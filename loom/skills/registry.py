"""
Skill Registry - 统一的Skill管理中心

负责：
1. 管理多个SkillLoader（文件系统/数据库等）
2. 运行时注册的 Skills（dict 格式，兼容 LoomApp/CapabilityRegistry）
3. 统一访问：先查运行时，再查 Loaders
4. Progressive Disclosure（渐进式加载）
"""

from collections.abc import Callable
from typing import Any

from .loader import SkillLoader
from .models import SkillDefinition


def _runtime_dict_to_skill_definition(skill_id: str, d: dict[str, Any]) -> SkillDefinition:
    """将运行时注册的 dict 转为 SkillDefinition，供 Agent/SkillActivator 使用"""
    fn = d.get("function", {})
    meta = d.get("_metadata", {}) if isinstance(d.get("_metadata"), dict) else {}
    return SkillDefinition(
        skill_id=skill_id,
        name=fn.get("name", skill_id),
        description=fn.get("description", ""),
        instructions=fn.get("description", ""),
        activation_criteria="",
        scripts={},
        references={},
        required_tools=meta.get("required_tools", []),
        metadata=meta,
        source="runtime",
    )


class SkillRegistry:
    """
    统一 Skill 注册表

    支持：Loader 来源（async get_skill/get_all_metadata）+ 运行时注册（register_skill）。
    先查运行时，再查 Loaders。
    """

    def __init__(self):
        """初始化Skill注册表"""
        self.loaders: list[SkillLoader] = []
        self._runtime_skills: dict[str, dict[str, Any]] = {}
        self._metadata_cache: list[dict] | None = None
        self._skills_cache: dict[str, SkillDefinition] | None = None

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
        运行时注册一个 Skill（兼容 LoomApp / dict 版 API）

        Args:
            name: Skill 名称（即 skill_id）
            description: 描述
            parameters: 参数定义（OpenAI 格式）
            handler: 处理函数
            source: 来源（python/mcp/http）
            ephemeral: 是否 ephemeral
            **metadata: 其他元数据（如 required_tools）

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
        self._runtime_skills[name] = skill_def
        self._metadata_cache = None
        self._skills_cache = None
        return skill_def

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
        获取单个Skill（先查运行时，再查 Loaders）

        Args:
            skill_id: Skill唯一标识

        Returns:
            SkillDefinition对象，如果不存在返回None
        """
        # 1. 先查运行时注册
        if skill_id in self._runtime_skills:
            return _runtime_dict_to_skill_definition(
                skill_id, self._runtime_skills[skill_id]
            )

        # 2. 尝试从缓存获取（Loader 加载的）
        if self._skills_cache and skill_id in self._skills_cache:
            return self._skills_cache[skill_id]

        # 3. 从所有 Loader 中查找
        for loader in self.loaders:
            skill = await loader.load_skill(skill_id)
            if skill:
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
        获取所有 Skills 的元数据（含运行时 + Loaders）

        Returns:
            元数据字典列表（含 skill_id, name, description 等）
        """
        if self._metadata_cache is not None:
            return self._metadata_cache

        metadata_list = []
        # 运行时注册的 Skill 元数据
        for skill_id, d in self._runtime_skills.items():
            fn = d.get("function", {})
            metadata_list.append({
                "skill_id": skill_id,
                "name": fn.get("name", skill_id),
                "description": fn.get("description", ""),
                "activation_criteria": "",
                "source": "runtime",
            })
        for loader in self.loaders:
            loader_metadata = await loader.list_skill_metadata()
            metadata_list.extend(loader_metadata)

        self._metadata_cache = metadata_list
        return metadata_list

    def list_skills(self) -> list[str]:
        """
        同步列出当前已知的 Skill ID（仅运行时注册部分，不含 Loader 延迟加载）

        用于 CapabilityRegistry 等需要同步列表的场景。
        完整列表请使用 list_skills_async()。
        """
        return list(self._runtime_skills.keys())

    async def list_skills_async(self) -> list[str]:
        """列出所有 Skill ID（运行时 + 各 Loader）"""
        seen = set(self._runtime_skills.keys())
        for loader in self.loaders:
            for skill in await loader.list_skills():
                seen.add(skill.skill_id)
        return list(seen)

    def get_skill_sync(self, skill_id: str) -> dict[str, Any] | None:
        """
        同步获取运行时注册的 Skill 定义（dict），仅查运行时，不查 Loaders。

        用于 CapabilityRegistry.validate_skill_dependencies 等同步场景。
        """
        return self._runtime_skills.get(skill_id)

    def get_skills_by_source(self, source: str) -> list[dict[str, Any]]:
        """按来源类型获取运行时注册的 Skills（兼容 LoomApp/dict 版 API）"""
        return [
            d for d in self._runtime_skills.values()
            if d.get("_source") == source
        ]

    def clear_cache(self) -> None:
        """清除缓存"""
        self._metadata_cache = None
        self._skills_cache = None
