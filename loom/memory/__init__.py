"""
A4: 记忆层次公理 (Memory Hierarchy Axiom)

三层记忆架构：
- L1 (MessageWindow): 滑动窗口 — 当前对话上下文
- L2 (WorkingMemoryLayer): 工作记忆 — session 内关键信息
- L3 (MemoryStore): 持久记忆 — 跨 session 用户级存储

导出内容：
- MemoryManager: 统一的记忆管理代理
- LoomMemory: 三层记忆系统核心
- MessageItem: L1 消息项
- WorkingMemoryEntry: L2 工作记忆条目
- MemoryRecord: L3 持久记忆记录
- MemoryStore: L3 存储后端 Protocol
- InMemoryStore: 内存实现的 MemoryStore
- MemoryTier: 记忆层级枚举 (L1/L2/L3)
- MemoryType: 记忆类型枚举
- MemoryStatus: 记忆状态枚举
- MemoryQuery: 记忆查询请求
- MessageWindow: L1 滑动窗口
- WorkingMemoryLayer: L2 工作记忆层
- TokenCounter / TiktokenCounter / EstimateCounter: Token 计数器
"""

from loom.memory.core import LoomMemory
from loom.memory.layers_merged import MessageWindow, WorkingMemoryLayer
from loom.memory.manager import MemoryManager
from loom.memory.shared_pool import PoolEntry, SharedMemoryPool, VersionConflictError
from loom.memory.store import InMemoryStore, MemoryStore
from loom.memory.tokenizer import (
    AnthropicCounter,
    EstimateCounter,
    TiktokenCounter,
    TokenCounter,
)
from loom.memory.types import (
    MemoryQuery,
    MemoryRecord,
    MemoryStatus,
    MemoryTier,
    MemoryType,
    MessageItem,
    WorkingMemoryEntry,
)

__all__ = [
    # Core
    "MemoryManager",
    "LoomMemory",
    # L1
    "MessageWindow",
    "MessageItem",
    # L2
    "WorkingMemoryLayer",
    "WorkingMemoryEntry",
    # L3
    "MemoryStore",
    "InMemoryStore",
    "MemoryRecord",
    # Types
    "MemoryTier",
    "MemoryType",
    "MemoryStatus",
    "MemoryQuery",
    # Tokenizer
    "TokenCounter",
    "TiktokenCounter",
    "AnthropicCounter",
    "EstimateCounter",
    # Shared
    "SharedMemoryPool",
    "PoolEntry",
    "VersionConflictError",
]
