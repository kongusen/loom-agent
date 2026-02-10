"""
Prompt Context Source - 系统提示词上下文源

管理系统提示词的上下文。
"""

from typing import TYPE_CHECKING

from loom.context.block import ContextBlock
from loom.context.source import ContextSource

if TYPE_CHECKING:
    from loom.memory.tokenizer import TokenCounter


class PromptSource(ContextSource):
    """
    系统提示词源

    系统提示词是固定开销，优先级高，不可压缩。
    """

    def __init__(self, system_prompt: str = ""):
        """
        初始化提示词源

        Args:
            system_prompt: 系统提示词
        """
        self._system_prompt = system_prompt

    @property
    def source_name(self) -> str:
        return "system_prompt"

    def set_prompt(self, prompt: str) -> None:
        """设置系统提示词"""
        self._system_prompt = prompt

    async def collect(
        self,
        query: str,
        token_budget: int,
        token_counter: "TokenCounter",
        min_relevance: float = 0.5,
    ) -> list[ContextBlock]:
        """收集系统提示词"""
        if not self._system_prompt:
            return []

        tokens = self._count_tokens(
            self._system_prompt, "system", token_counter
        )

        block = ContextBlock(
            content=self._system_prompt,
            role="system",
            token_count=tokens,
            priority=0.95,  # 高优先级
            source=self.source_name,
            compressible=False,  # 不可压缩
            metadata={"type": "system_prompt"},
        )

        return [block]
