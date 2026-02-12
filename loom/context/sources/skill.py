"""
Skill Context Source - 技能定义上下文源

从技能注册表获取技能定义作为上下文。
"""

from typing import TYPE_CHECKING, Any

from loom.context.block import ContextBlock
from loom.context.source import ContextSource

if TYPE_CHECKING:
    from loom.memory.tokenizer import TokenCounter


class SkillSource(ContextSource):
    """
    技能定义源

    按需激活技能到上下文中。
    技能通过注入方式添加到系统提示词。
    """

    def __init__(
        self,
        skill_registry: Any = None,
        active_skill_ids: list[str] | None = None,
    ):
        """
        初始化技能源

        Args:
            skill_registry: SkillRegistry 实例
            active_skill_ids: 已激活的技能ID列表
        """
        self._skill_registry = skill_registry
        self._active_skill_ids = active_skill_ids or []

    @property
    def source_name(self) -> str:
        return "skills"

    def activate_skill(self, skill_id: str) -> None:
        """激活技能"""
        if skill_id not in self._active_skill_ids:
            self._active_skill_ids.append(skill_id)

    def deactivate_skill(self, skill_id: str) -> None:
        """停用技能"""
        if skill_id in self._active_skill_ids:
            self._active_skill_ids.remove(skill_id)

    def set_active_skills(self, skill_ids: list[str]) -> None:
        """设置激活的技能列表"""
        self._active_skill_ids = list(skill_ids)

    async def _get_skill_content(self, skill_id: str) -> str | None:
        """获取技能内容"""
        if not self._skill_registry:
            return None

        try:
            import asyncio

            get_fn = getattr(self._skill_registry, "get_skill", None)
            if get_fn and asyncio.iscoroutinefunction(get_fn):
                skill_def = await get_fn(skill_id)
            else:
                skill_def = get_fn(skill_id) if get_fn else None

            if not skill_def:
                return None

            if hasattr(skill_def, "get_full_instructions"):
                return str(skill_def.get_full_instructions())
            elif hasattr(skill_def, "instructions"):
                return str(skill_def.instructions)

            return None
        except Exception:
            return None

    async def collect(
        self,
        query: str,
        token_budget: int,
        token_counter: "TokenCounter",
        min_relevance: float = 0.5,
    ) -> list[ContextBlock]:
        """收集激活的技能内容"""
        if not self._active_skill_ids:
            return []

        blocks: list[ContextBlock] = []
        current_tokens = 0

        for skill_id in self._active_skill_ids:
            content = await self._get_skill_content(skill_id)
            if not content:
                continue

            tokens = self._count_tokens(content, "system", token_counter)
            if current_tokens + tokens > token_budget:
                break

            block = ContextBlock(
                content=content,
                role="system",
                token_count=tokens,
                priority=0.85,
                source=self.source_name,
                compressible=False,
                metadata={"skill_id": skill_id},
            )
            blocks.append(block)
            current_tokens += tokens

        return blocks
