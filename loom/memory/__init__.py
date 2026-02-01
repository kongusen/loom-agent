"""
A4: 记忆层次公理 (Memory Hierarchy Axiom)

公理陈述：Memory = L1 ⊂ L2 ⊂ L3 ⊂ L4

本模块实现统一的记忆管理系统，整合四层记忆（L1-L4）和作用域管理。

导出内容：
- MemoryManager: 统一的记忆管理系统（L1-L4 + 作用域）
- LoomMemory: L1-L4 层记忆实现（底层组件）
- MemoryUnit: 记忆单元
- MemoryTier: 记忆层级枚举
- MemoryType: 记忆类型枚举
- MemoryStatus: 记忆状态枚举
- MemoryQuery: 记忆查询请求
- ContentSanitizer: 内容清理器
- MemoryFactory: 记忆工厂
- L4Compressor: L4记忆压缩器
- VectorStoreProvider: 向量存储接口
- InMemoryVectorStore: 内存向量存储实现
- EmbeddingProvider: 嵌入提供者接口
- TokenCounter: Token 计数器抽象接口
- TiktokenCounter: OpenAI Tiktoken 计数器
- AnthropicCounter: Anthropic 计数器
- EstimateCounter: 估算计数器
- ContextStrategy: 上下文选择策略抽象接口
- PriorityContextStrategy: 基于优先级的上下文策略
- SlidingWindowStrategy: 滑动窗口上下文策略
- ContextManager: 上下文管理器
"""

from loom.memory.compression import L4Compressor
from loom.memory.context import (
    ContextManager,
    ContextStrategy,
    PriorityContextStrategy,
    SlidingWindowStrategy,
)
from loom.memory.core import LoomMemory
from loom.memory.factory import MemoryFactory
from loom.memory.manager import MemoryManager
from loom.memory.sanitizers import ContentSanitizer
from loom.memory.tokenizer import (
    AnthropicCounter,
    EstimateCounter,
    TiktokenCounter,
    TokenCounter,
)
from loom.memory.types import (
    MemoryQuery,
    MemoryStatus,
    MemoryTier,
    MemoryType,
    MemoryUnit,
)
from loom.memory.vector_store import (
    EmbeddingProvider,
    InMemoryVectorStore,
    VectorStoreProvider,
)

__all__ = [
    "MemoryManager",
    "LoomMemory",
    "MemoryUnit",
    "MemoryTier",
    "MemoryType",
    "MemoryStatus",
    "MemoryQuery",
    "ContentSanitizer",
    "MemoryFactory",
    "L4Compressor",
    "VectorStoreProvider",
    "InMemoryVectorStore",
    "EmbeddingProvider",
    "TokenCounter",
    "TiktokenCounter",
    "AnthropicCounter",
    "EstimateCounter",
    "ContextStrategy",
    "PriorityContextStrategy",
    "SlidingWindowStrategy",
    "ContextManager",
]
