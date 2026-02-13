"""
记忆系统类型定义 — 三层架构

三层模型：
- L1 (Window): 滑动窗口，存储原始 messages[]，session 级，内存
- L2 (Working): 工作记忆，存储 facts/decisions，session 级，内存
- L3 (Persistent): 持久记忆，跨 session，LLM 摘要 + 可选向量检索

设计原则：
1. Token-First Design — 所有层以 token 预算控制容量
2. Message-Native — L1 直接存储 LLM messages，不再转换为 Task
3. 框架提供机制，应用选择策略
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# =============================================================================
# 层级枚举
# =============================================================================


class MemoryTier(Enum):
    """
    记忆层级 (三层)

    L1 ⊂ L2 ⊂ L3
    - L1: 滑动窗口（当前对话上下文）
    - L2: 工作记忆（session 内关键信息）
    - L3: 持久记忆（跨 session，用户级）
    """

    L1_WINDOW = 1
    L2_WORKING = 2
    L3_PERSISTENT = 3


class MemoryType(Enum):
    """记忆内容类型"""

    MESSAGE = "message"
    THOUGHT = "thought"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    PLAN = "plan"
    FACT = "fact"
    DECISION = "decision"
    SUMMARY = "summary"
    CONTEXT = "context"


class MemoryStatus(Enum):
    """记忆单元生命周期状态"""

    ACTIVE = "active"
    ARCHIVED = "archived"
    SUMMARIZED = "summarized"
    EVICTED = "evicted"


# =============================================================================
# L1: MessageItem — 滑动窗口中的单条消息
# =============================================================================


@dataclass
class MessageItem:
    """
    L1 滑动窗口中的单条消息

    直接对应 LLM API 的 message 格式，保留完整的对话结构。
    支持 tool_call 配对驱逐（驱逐 tool_call 时同时驱逐对应的 tool_result）。

    Attributes:
        role: 消息角色 ("user", "assistant", "system", "tool")
        content: 消息内容（文本或结构化内容）
        token_count: 该消息的 token 数
        message_id: 唯一标识
        tool_call_id: 工具调用 ID（用于 tool_call/tool_result 配对）
        tool_name: 工具名称（仅 tool_call 类型）
        tool_calls: 原始 tool_calls 列表（assistant 消息中的工具调用）
        created_at: 创建时间
        metadata: 扩展元数据
    """

    role: str
    content: str | dict[str, Any] | None = None
    token_count: int = 0
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_message(self) -> dict[str, Any]:
        """
        转换为 LLM API message 格式

        Returns:
            符合 OpenAI/Anthropic API 格式的消息字典
        """
        msg: dict[str, Any] = {"role": self.role}

        if self.content is not None:
            msg["content"] = self.content

        # assistant 消息可能包含 tool_calls
        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls

        # tool 消息需要 tool_call_id
        if self.role == "tool" and self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id

        # tool 消息可能有 name
        if self.tool_name:
            msg["name"] = self.tool_name

        return msg

    @classmethod
    def from_message(cls, msg: dict[str, Any], token_count: int = 0) -> "MessageItem":
        """
        从 LLM API message 格式创建 MessageItem

        Args:
            msg: LLM API 消息字典
            token_count: 预计算的 token 数

        Returns:
            MessageItem 实例
        """
        return cls(
            role=msg.get("role", "user"),
            content=msg.get("content"),
            token_count=token_count,
            tool_call_id=msg.get("tool_call_id"),
            tool_name=msg.get("name"),
            tool_calls=msg.get("tool_calls"),
        )


# =============================================================================
# L2: WorkingMemoryEntry — 工作记忆条目
# =============================================================================


class FactType(Enum):
    """事实类型 — 分类可复用的原子知识"""

    API_SCHEMA = "api_schema"
    USER_PREFERENCE = "user_preference"
    DOMAIN_KNOWLEDGE = "domain_knowledge"
    TOOL_USAGE = "tool_usage"
    ERROR_PATTERN = "error_pattern"
    BEST_PRACTICE = "best_practice"
    CONVERSATION_SUMMARY = "conversation_summary"


@dataclass
class WorkingMemoryEntry:
    """
    L2 工作记忆条目

    存储从 L1 驱逐消息中提取的关键信息：
    - 事实 (facts)
    - 决策 (decisions)
    - 对话摘要 (conversation summaries)

    Attributes:
        entry_id: 唯一标识
        content: 条目内容（简洁文本）
        entry_type: 条目类型
        importance: 重要性 (0.0-1.0)
        token_count: token 数
        tags: 标签列表
        source_message_ids: 来源消息 ID 列表
        created_at: 创建时间
        session_id: 所属 session
        access_count: 访问次数
        metadata: 扩展元数据
    """

    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    entry_type: MemoryType = MemoryType.FACT
    importance: float = 0.5
    token_count: int = 0
    tags: list[str] = field(default_factory=list)
    source_message_ids: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    session_id: str | None = None
    access_count: int = 0
    expires_at: datetime | None = None  # L2 TTL 过期时间
    metadata: dict[str, Any] = field(default_factory=dict)

    def update_access(self) -> None:
        """更新访问信息"""
        self.access_count += 1


# =============================================================================
# L3: MemoryRecord — 持久记忆记录
# =============================================================================


@dataclass
class MemoryRecord:
    """
    L3 持久记忆记录

    跨 session 的持久化记忆，由 LLM 生成摘要，可选向量检索。
    按 user_id 隔离，支持多用户多 session。

    Attributes:
        record_id: 唯一标识
        content: LLM 生成的摘要文本
        user_id: 所属用户（多用户隔离）
        session_id: 来源 session
        importance: 重要性 (0.0-1.0)
        tags: 标签列表
        embedding: 向量嵌入（可选，用于语义检索）
        created_at: 创建时间
        source_entry_ids: 来源 L2 条目 ID 列表
        metadata: 扩展元数据
    """

    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    user_id: str | None = None
    session_id: str | None = None
    importance: float = 0.5
    tags: list[str] = field(default_factory=list)
    embedding: list[float] | None = None
    created_at: datetime = field(default_factory=datetime.now)
    source_entry_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# 查询类型
# =============================================================================


@dataclass
class MemoryQuery:
    """记忆查询请求"""

    query: str
    tier: MemoryTier | None = None
    type: MemoryType | None = None
    limit: int = 10
    min_importance: float = 0.0
    user_id: str | None = None
    session_id: str | None = None
