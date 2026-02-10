"""
Context Compactor - 上下文压缩器

当上下文超过预算时，智能压缩低优先级内容。
基于 Anthropic Context Compaction 思想。
"""

from enum import Enum
from typing import TYPE_CHECKING, Awaitable, Callable

from loom.context.block import ContextBlock

if TYPE_CHECKING:
    from loom.memory.tokenizer import TokenCounter


class CompactionLevel(Enum):
    """压缩级别"""

    NONE = 0  # 不压缩
    LIGHT = 1  # 轻度：移除冗余
    MEDIUM = 2  # 中度：摘要替代
    AGGRESSIVE = 3  # 激进：只保留关键信息


class ContextCompactor:
    """
    上下文压缩器

    职责：
    1. 检测是否需要压缩
    2. 按优先级保留高价值内容
    3. 压缩或丢弃低优先级内容
    """

    def __init__(
        self,
        token_counter: "TokenCounter",
        summarizer: Callable[[str], Awaitable[str]] | None = None,
    ):
        """
        初始化压缩器

        Args:
            token_counter: Token 计数器
            summarizer: 摘要生成函数（可选）
        """
        self.token_counter = token_counter
        self.summarizer = summarizer

    def get_compaction_level(
        self,
        total_tokens: int,
        budget: int,
    ) -> CompactionLevel:
        """
        决定压缩级别

        Args:
            total_tokens: 当前总 token 数
            budget: 预算

        Returns:
            CompactionLevel
        """
        if budget <= 0:
            return CompactionLevel.AGGRESSIVE

        ratio = total_tokens / budget

        if ratio < 0.7:
            return CompactionLevel.NONE
        elif ratio < 0.85:
            return CompactionLevel.LIGHT
        elif ratio < 0.95:
            return CompactionLevel.MEDIUM
        else:
            return CompactionLevel.AGGRESSIVE

    async def compact(
        self,
        blocks: list[ContextBlock],
        target_tokens: int,
    ) -> list[ContextBlock]:
        """
        压缩上下文块到目标 token 数

        策略：
        1. 按 priority 降序排序
        2. 保留高优先级不可压缩块
        3. 对可压缩块进行压缩
        4. 丢弃最低优先级块

        Args:
            blocks: 上下文块列表
            target_tokens: 目标 token 数

        Returns:
            压缩后的块列表
        """
        if not blocks:
            return []

        total_tokens = sum(b.token_count for b in blocks)
        if total_tokens <= target_tokens:
            return blocks

        # 按 priority 降序排序
        sorted_blocks = sorted(blocks, key=lambda b: b.priority, reverse=True)

        # 分离不可压缩和可压缩块
        non_compressible = [b for b in sorted_blocks if not b.compressible]
        compressible = [b for b in sorted_blocks if b.compressible]

        # 计算不可压缩块占用
        non_comp_tokens = sum(b.token_count for b in non_compressible)

        # 如果不可压缩块已超预算，只能丢弃低优先级的不可压缩块
        if non_comp_tokens > target_tokens:
            return self._fit_to_budget(non_compressible, target_tokens)

        # 剩余预算给可压缩块
        remaining_budget = target_tokens - non_comp_tokens

        # 压缩可压缩块
        compacted = await self._compact_blocks(compressible, remaining_budget)

        return non_compressible + compacted

    def _fit_to_budget(
        self,
        blocks: list[ContextBlock],
        budget: int,
    ) -> list[ContextBlock]:
        """按预算截取块（已按 priority 排序）"""
        result: list[ContextBlock] = []
        current_tokens = 0

        for block in blocks:
            if current_tokens + block.token_count <= budget:
                result.append(block)
                current_tokens += block.token_count
            else:
                break

        return result

    async def _compact_blocks(
        self,
        blocks: list[ContextBlock],
        budget: int,
    ) -> list[ContextBlock]:
        """压缩块列表到预算内"""
        if not blocks:
            return []

        total_tokens = sum(b.token_count for b in blocks)
        level = self.get_compaction_level(total_tokens, budget)

        if level == CompactionLevel.NONE:
            return self._fit_to_budget(blocks, budget)

        result: list[ContextBlock] = []
        current_tokens = 0

        for block in blocks:
            if current_tokens >= budget:
                break

            remaining = budget - current_tokens

            # 尝试压缩
            compacted = await self._compact_single(block, level, remaining)
            if compacted:
                result.append(compacted)
                current_tokens += compacted.token_count

        return result

    async def _compact_single(
        self,
        block: ContextBlock,
        level: CompactionLevel,
        max_tokens: int,
    ) -> ContextBlock | None:
        """
        压缩单个块

        Args:
            block: 要压缩的块
            level: 压缩级别
            max_tokens: 最大允许 token 数

        Returns:
            压缩后的块，如果无法压缩到预算内则返回 None
        """
        # 如果已经在预算内，直接返回
        if block.token_count <= max_tokens:
            return block

        # 根据级别压缩
        if level == CompactionLevel.LIGHT:
            return self._light_compact(block, max_tokens)
        elif level == CompactionLevel.MEDIUM:
            return await self._medium_compact(block, max_tokens)
        elif level == CompactionLevel.AGGRESSIVE:
            return await self._aggressive_compact(block, max_tokens)

        return None

    def _light_compact(
        self,
        block: ContextBlock,
        max_tokens: int,
    ) -> ContextBlock | None:
        """轻度压缩：移除空行和冗余空格"""
        content = block.content

        # 移除多余空行
        lines = content.split("\n")
        cleaned_lines = []
        prev_empty = False
        for line in lines:
            stripped = line.strip()
            is_empty = not stripped
            if is_empty and prev_empty:
                continue
            cleaned_lines.append(line.rstrip())
            prev_empty = is_empty

        new_content = "\n".join(cleaned_lines)
        new_tokens = self.token_counter.count_messages(
            [{"role": block.role, "content": new_content}]
        )

        if new_tokens <= max_tokens:
            return block.with_content(new_content, new_tokens)

        # 如果还是超预算，截断
        return self._truncate_to_budget(block, new_content, max_tokens)

    async def _medium_compact(
        self,
        block: ContextBlock,
        max_tokens: int,
    ) -> ContextBlock | None:
        """中度压缩：生成摘要"""
        if self.summarizer:
            try:
                summary = await self.summarizer(block.content)
                new_tokens = self.token_counter.count_messages(
                    [{"role": block.role, "content": summary}]
                )
                if new_tokens <= max_tokens:
                    return block.with_content(summary, new_tokens)
            except Exception:
                pass

        # 降级到轻度压缩
        return self._light_compact(block, max_tokens)

    async def _aggressive_compact(
        self,
        block: ContextBlock,
        max_tokens: int,
    ) -> ContextBlock | None:
        """激进压缩：提取关键句或截断"""
        # 先尝试中度压缩
        result = await self._medium_compact(block, max_tokens)
        if result and result.token_count <= max_tokens:
            return result

        # 最后手段：截断
        return self._truncate_to_budget(block, block.content, max_tokens)

    def _truncate_to_budget(
        self,
        block: ContextBlock,
        content: str,
        max_tokens: int,
    ) -> ContextBlock | None:
        """截断内容到预算内"""
        if max_tokens <= 0:
            return None

        # 二分查找合适的截断点
        low, high = 0, len(content)
        best_content = ""
        best_tokens = 0

        while low < high:
            mid = (low + high + 1) // 2
            truncated = content[:mid] + "..."
            tokens = self.token_counter.count_messages(
                [{"role": block.role, "content": truncated}]
            )

            if tokens <= max_tokens:
                best_content = truncated
                best_tokens = tokens
                low = mid
            else:
                high = mid - 1

        if best_content:
            return block.with_content(best_content, best_tokens)

        return None
