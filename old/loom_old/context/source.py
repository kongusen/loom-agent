"""
Context Source - 上下文源抽象接口

定义从不同来源获取上下文的统一接口。
完全基于 Token，不使用条目计数。
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from loom.context.block import ContextBlock

if TYPE_CHECKING:
    from loom.memory.tokenizer import TokenCounter


class ContextSource(ABC):
    """
    上下文源 - 完全基于 Token

    设计原则：
    1. Token-First: 所有操作以 token 为单位
    2. Quality over Quantity: 低相关性内容不返回
    3. Budget-Aware: 严格遵守 token 预算
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """
        源名称

        用于日志、调试和预算分配。
        例如: "L1_recent", "L2_important", "RAG_knowledge"
        """
        pass

    @abstractmethod
    async def collect(
        self,
        query: str,
        token_budget: int,
        token_counter: "TokenCounter",
        min_relevance: float = 0.5,
    ) -> list[ContextBlock]:
        """
        收集上下文块

        Args:
            query: 当前任务内容，用于相关性计算
            token_budget: 分配给此源的 token 预算
            token_counter: Token 计数器
            min_relevance: 最低相关性阈值 (0.0-1.0)

        Returns:
            ContextBlock 列表，总 token 数不超过 token_budget

        Note:
            - 低于 min_relevance 的内容不返回
            - 返回的块按 priority 降序排列
        """
        pass

    def _count_tokens(
        self,
        content: str,
        role: str,
        token_counter: "TokenCounter",
    ) -> int:
        """计算内容的 token 数"""
        return token_counter.count_messages([{"role": role, "content": content}])

    def _fits_budget(
        self,
        blocks: list[ContextBlock],
        new_block: ContextBlock,
        token_budget: int,
    ) -> bool:
        """检查添加新块后是否超预算"""
        current_tokens = sum(b.token_count for b in blocks)
        return current_tokens + new_block.token_count <= token_budget
