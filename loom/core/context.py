"""
上下文管理 - 压缩、重建、组装

职责：
1. 长上下文压缩
2. 状态重建
3. Memory 集成
4. Context 优化
"""

from __future__ import annotations
from typing import List, Optional
from loom.core.message import Message, get_message_history
from loom.core.errors import ContextError
from loom.interfaces.memory import BaseMemory
from loom.interfaces.compressor import BaseCompressor
from loom.utils.token_counter import estimate_tokens


class ContextManager:
    """
    Context 管理器

    核心功能：
    - 自动压缩长上下文
    - 智能状态重建
    - Memory 集成
    - Context 优化

    特性：
    - 自动检测是否需要压缩
    - 保留重要的系统消息
    - 集成 Memory（如果提供）
    - 优化 Context 结构

    示例：
    ```python
    from loom.core.context import ContextManager
    from loom.builtin.compression import StructuredCompressor

    manager = ContextManager(
        compressor=StructuredCompressor(),
        memory=some_memory,
        max_context_tokens=100000
    )

    # 准备 Context（自动压缩和优化）
    optimized_message = await manager.prepare(message)
    ```
    """

    def __init__(
        self,
        compressor: Optional[BaseCompressor] = None,
        memory: Optional[BaseMemory] = None,
        max_context_tokens: int = 100000,
        compression_threshold: float = 0.8,  # 80% 就开始压缩
    ):
        """
        初始化 Context 管理器

        Args:
            compressor: 压缩器（可选）
            memory: Memory 系统（可选）
            max_context_tokens: 最大 Context token 数
            compression_threshold: 压缩阈值（比例）
        """
        self.compressor = compressor
        self.memory = memory
        self.max_context_tokens = max_context_tokens
        self.compression_threshold = compression_threshold

    async def prepare(self, message: Message) -> Message:
        """
        准备 Context

        流程：
        1. 获取完整历史
        2. 检查是否需要压缩
        3. 如果需要，触发压缩
        4. 如果有 Memory，加载相关内容
        5. 返回优化后的 Message

        Args:
            message: 输入消息

        Returns:
            优化后的消息（包含压缩和 Memory 增强的 Context）

        Raises:
            ContextError: Context 管理错误
        """
        try:
            # 1. 获取完整历史
            messages = self._get_history(message)

            # 2. 检查是否需要压缩
            if self._need_compression(messages):
                messages = await self._compress(messages)

            # 3. 如果有 Memory，加载相关内容
            if self.memory:
                messages = await self._enhance_with_memory(messages, message.content)

            # 4. 构建新 Message（包含优化后的历史）
            return message.with_history(messages)

        except Exception as e:
            raise ContextError(f"Failed to prepare context: {str(e)}") from e

    def _get_history(self, message: Message) -> List[Message]:
        """获取消息历史（v0.1.9: 使用安全提取）"""
        return get_message_history(message)

    def _need_compression(self, messages: List[Message]) -> bool:
        """
        检查是否需要压缩

        Args:
            messages: 消息列表

        Returns:
            是否需要压缩
        """
        # 计算总 token 数
        total_tokens = sum(estimate_tokens(m.content) for m in messages)

        # 超过阈值就需要压缩
        threshold = self.max_context_tokens * self.compression_threshold
        return total_tokens > threshold

    async def _compress(self, messages: List[Message]) -> List[Message]:
        """
        压缩 Context

        Args:
            messages: 消息列表

        Returns:
            压缩后的消息列表

        Raises:
            CompressionError: 压缩失败
        """
        if not self.compressor:
            # 如果没有 compressor，使用简单截断策略
            return self._simple_truncate(messages)

        # 使用 compressor 压缩
        try:
            # 分离系统消息和其他消息
            system_messages = [m for m in messages if m.role == "system"]
            other_messages = [m for m in messages if m.role != "system"]

            # 压缩其他消息（保留系统消息）
            if len(other_messages) > 0:
                compressed = await self.compressor.compress(other_messages)
                # 合并：系统消息在前
                return system_messages + compressed
            else:
                return messages

        except Exception as e:
            from loom.core.errors import CompressionError

            raise CompressionError(f"Compression failed: {str(e)}") from e

    def _simple_truncate(self, messages: List[Message]) -> List[Message]:
        """
        简单的截断策略（当没有 compressor 时使用）

        保留：
        - 所有系统消息
        - 前 2 条消息（保留上下文）
        - 最后 10 条消息（保留最近对话）

        Args:
            messages: 消息列表

        Returns:
            截断后的消息列表
        """
        if len(messages) <= 13:  # 系统消息 + 前2条 + 后10条
            return messages

        # 分离系统消息
        system_messages = [m for m in messages if m.role == "system"]
        other_messages = [m for m in messages if m.role != "system"]

        if len(other_messages) <= 12:
            return system_messages + other_messages

        # 保留前2条和后10条
        kept_messages = other_messages[:2] + other_messages[-10:]

        # 合并
        return system_messages + kept_messages

    async def _enhance_with_memory(
        self, messages: List[Message], query: str
    ) -> List[Message]:
        """
        使用 Memory 增强 Context

        Args:
            messages: 消息列表
            query: 查询内容

        Returns:
            增强后的消息列表
        """
        if not self.memory:
            return messages

        try:
            # 从 Memory 检索相关内容（使用新的 retrieve() 方法）
            # 所有 Memory 实现都支持此方法（默认返回空字符串）
            relevant = await self.memory.retrieve(
                query=query,
                top_k=5,
                tier="longterm",  # 优先检索长期记忆
            )

            if relevant:
                # 创建 Memory 消息
                # Note: relevant 可能已经是 XML 格式（如 HierarchicalMemory）
                # 为了兼容性，我们在外面加上标题
                content = f"## Relevant Context from Memory\n\n{relevant}"

                memory_message = Message(
                    role="system",
                    content=content,
                    name="memory",
                )

                # 插入到系统消息之后
                # 找到最后一个系统消息的位置
                last_system_idx = -1
                for i, m in enumerate(messages):
                    if m.role == "system":
                        last_system_idx = i

                if last_system_idx >= 0:
                    # 插入到最后一个系统消息之后
                    messages.insert(last_system_idx + 1, memory_message)
                else:
                    # 如果没有系统消息，插入到最前面
                    messages.insert(0, memory_message)

        except Exception as e:
            # Memory 失败不应该阻止执行，只记录警告
            import logging

            logging.warning(f"Failed to retrieve from memory: {str(e)}")

        return messages

    def get_stats(self) -> dict:
        """
        获取 Context 统计信息

        Returns:
            统计信息字典
        """
        return {
            "max_context_tokens": self.max_context_tokens,
            "compression_threshold": self.compression_threshold,
            "has_compressor": self.compressor is not None,
            "has_memory": self.memory is not None,
        }


# ============================================================================
# 便捷函数
# ============================================================================


def create_context_manager(
    compressor: Optional[str] = None,
    memory: Optional[str] = None,
    max_context_tokens: int = 100000,
    **kwargs,
) -> ContextManager:
    """
    创建 ContextManager 的便捷函数

    Args:
        compressor: 压缩器类型
            - "structured": StructuredCompressor
            - None: 不使用压缩器
        memory: Memory 类型
            - "in_memory": InMemoryMemory
            - "persistent": PersistentMemory
            - None: 不使用 Memory
        max_context_tokens: 最大 Context token 数
        **kwargs: 其他参数

    Returns:
        ContextManager 实例

    Examples:
        ```python
        # 使用默认配置
        manager = create_context_manager()

        # 使用压缩器
        manager = create_context_manager(compressor="structured")

        # 使用 Memory
        manager = create_context_manager(
            compressor="structured",
            memory="in_memory"
        )
        ```
    """
    compressor_instance = None
    if compressor == "structured":
        from loom.builtin.compression import StructuredCompressor

        compressor_instance = StructuredCompressor()

    memory_instance = None
    if memory == "in_memory":
        from loom.builtin.memory import InMemoryMemory

        memory_instance = InMemoryMemory()
    elif memory == "persistent":
        from loom.builtin.memory import PersistentMemory

        memory_instance = PersistentMemory(**kwargs)

    return ContextManager(
        compressor=compressor_instance,
        memory=memory_instance,
        max_context_tokens=max_context_tokens,
        **kwargs,
    )
