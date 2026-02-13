"""
Memory Context Sources — 从 3 层记忆系统获取上下文

L1WindowSource: L1 滑动窗口消息（对话历史）
L2WorkingSource: L2 工作记忆（facts/decisions/summaries）
L3PersistentSource: L3 持久记忆（跨 session 检索）
"""

from typing import TYPE_CHECKING

from loom.context.block import ContextBlock
from loom.context.source import ContextSource

if TYPE_CHECKING:
    from loom.memory.core import LoomMemory
    from loom.memory.tokenizer import TokenCounter


class L1WindowSource(ContextSource):
    """
    L1 滑动窗口源 — 当前对话历史

    从 LoomMemory 的 L1 MessageWindow 获取消息。
    每条消息保持原始 role（user/assistant/tool），
    优先级按时间递增（最近的消息优先级最高）。

    注意：在新架构中，L1 消息通常由 ExecutionEngine 直接
    通过 memory.get_context_messages() 获取，不经过
    ContextOrchestrator。此源主要用于需要将 L1 消息
    纳入统一预算管理的场景。
    """

    def __init__(
        self,
        memory: "LoomMemory",
        session_id: str | None = None,
    ):
        self.memory = memory
        self.session_id = session_id

    @property
    def source_name(self) -> str:
        return "L1_window"

    async def collect(
        self,
        query: str,
        token_budget: int,
        token_counter: "TokenCounter",
        min_relevance: float = 0.5,
    ) -> list[ContextBlock]:
        """收集 L1 滑动窗口中的消息"""
        items = self.memory.get_message_items()
        if not items:
            return []

        blocks: list[ContextBlock] = []
        current_tokens = 0
        total = len(items)

        # 从最近的消息开始（倒序遍历），保证最新消息优先入选
        for idx, item in enumerate(reversed(items)):
            # 跳过 system 消息（由 PromptSource 处理）
            if item.role == "system":
                continue

            content = str(item.content) if item.content else ""
            if not content and not item.tool_calls:
                continue

            # 构建内容：普通消息用 content，tool_call 消息附加工具信息
            display_content = content
            if item.tool_calls:
                tool_names = [
                    tc.get("function", {}).get("name", "?")
                    for tc in item.tool_calls
                ]
                if content:
                    display_content = f"{content}\n[Tools: {', '.join(tool_names)}]"
                else:
                    display_content = f"[Tools: {', '.join(tool_names)}]"

            tokens = item.token_count or self._count_tokens(
                display_content, item.role, token_counter,
            )

            if current_tokens + tokens > token_budget:
                break

            # 优先级：最近 = 1.0，最旧 = 0.5
            priority = 1.0 - (idx / max(total, 1)) * 0.5

            # 映射 role（tool → assistant，保持 ContextBlock 兼容）
            role = item.role if item.role in ("user", "assistant", "system") else "assistant"

            block = ContextBlock(
                content=display_content,
                role=role,
                token_count=tokens,
                priority=priority,
                source=self.source_name,
                compressible=True,
                metadata={
                    "message_id": item.message_id,
                    "original_role": item.role,
                    "tool_call_id": item.tool_call_id,
                    "tool_name": item.tool_name,
                },
            )
            blocks.append(block)
            current_tokens += tokens

        # 反转回时间顺序（collect 时倒序遍历，输出要正序）
        blocks.reverse()
        return blocks


class L2WorkingSource(ContextSource):
    """
    L2 工作记忆源 — session 内关键信息

    从 LoomMemory 的 L2 WorkingMemoryLayer 获取条目。
    这些是从 L1 驱逐消息中提取的 facts/decisions/summaries，
    作为 system 消息注入上下文，帮助 LLM 记住重要信息。

    优先级基于条目的 importance 字段。
    """

    def __init__(
        self,
        memory: "LoomMemory",
        session_id: str | None = None,
    ):
        self.memory = memory
        self.session_id = session_id

    @property
    def source_name(self) -> str:
        return "L2_working"

    async def collect(
        self,
        query: str,
        token_budget: int,
        token_counter: "TokenCounter",
        min_relevance: float = 0.5,
    ) -> list[ContextBlock]:
        """收集 L2 工作记忆条目"""
        entries = self.memory.get_working_memory()
        if not entries:
            return []

        blocks: list[ContextBlock] = []
        current_tokens = 0

        for entry in entries:
            if not entry.content:
                continue

            # 格式化为系统消息
            label = entry.entry_type.value.upper()
            content = f"[Working Memory / {label}] {entry.content}"

            tokens = entry.token_count or self._count_tokens(
                content, "system", token_counter,
            )

            if current_tokens + tokens > token_budget:
                break

            priority = min(1.0, max(0.0, entry.importance))

            # 过滤低重要性
            if priority < min_relevance:
                continue

            block = ContextBlock(
                content=content,
                role="system",
                token_count=tokens,
                priority=priority,
                source=self.source_name,
                compressible=True,
                metadata={
                    "entry_id": entry.entry_id,
                    "entry_type": entry.entry_type.value,
                    "tags": entry.tags,
                },
            )
            blocks.append(block)
            current_tokens += tokens

        return blocks


class L3PersistentSource(ContextSource):
    """
    L3 持久记忆源 — 跨 session 检索

    从 LoomMemory 的 L3 MemoryStore 检索相关记忆。
    支持文本匹配和向量语义检索。
    作为 system 消息注入上下文。

    替代旧的 L4SemanticSource，因为新架构中
    L3 已合并了旧 L3（文本）和 L4（向量）的功能。
    """

    def __init__(
        self,
        memory: "LoomMemory",
        session_id: str | None = None,
    ):
        self.memory = memory
        self.session_id = session_id

    @property
    def source_name(self) -> str:
        return "L3_persistent"

    async def collect(
        self,
        query: str,
        token_budget: int,
        token_counter: "TokenCounter",
        min_relevance: float = 0.5,
    ) -> list[ContextBlock]:
        """检索 L3 持久记忆"""
        if not query:
            return []

        # 检查是否有 L3 存储
        if self.memory.l3 is None:
            return []

        # 文本检索
        try:
            records = await self.memory.search_persistent(
                query=query,
                limit=20,
            )
        except Exception:
            return []

        if not records:
            return []

        blocks: list[ContextBlock] = []
        current_tokens = 0

        for record in records:
            if not record.content:
                continue

            content = f"[Persistent Memory] {record.content}"
            tokens = self._count_tokens(content, "system", token_counter)

            if current_tokens + tokens > token_budget:
                break

            priority = min(1.0, max(0.0, record.importance))

            if priority < min_relevance:
                continue

            block = ContextBlock(
                content=content,
                role="system",
                token_count=tokens,
                priority=priority,
                source=self.source_name,
                compressible=True,
                metadata={
                    "record_id": record.record_id,
                    "tags": record.tags,
                    "session_id": record.session_id,
                },
            )
            blocks.append(block)
            current_tokens += tokens

        return blocks
