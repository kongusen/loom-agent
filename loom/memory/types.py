"""
记忆系统类型定义

基于A4公理（记忆层次公理）的实现

设计原则：
1. Token-First Design - 所有记忆单元携带 token 计数
2. Quality over Quantity - 通过 importance 和 information_density 评估质量
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MemoryTier(Enum):
    """
    记忆层级 (L1-L4)

    基于A4公理：Memory = L1 ⊂ L2 ⊂ L3 ⊂ L4
    """

    L1_RAW_IO = 1  # 原始IO（工作记忆）
    L2_WORKING = 2  # 工作记忆（会话重要内容）
    L3_SESSION = 3  # 会话记忆（摘要）
    L4_GLOBAL = 4  # 跨会话记忆（向量化）


class MemoryType(Enum):
    """
    记忆内容类型

    用于分类和过滤
    """

    MESSAGE = "message"  # 对话消息
    THOUGHT = "thought"  # 内部思考
    TOOL_CALL = "tool_call"  # 工具调用
    TOOL_RESULT = "tool_result"  # 工具结果
    PLAN = "plan"  # 计划
    FACT = "fact"  # 事实知识
    CONTEXT = "context"  # 上下文片段
    SUMMARY = "summary"  # 摘要


class MemoryStatus(Enum):
    """
    记忆单元状态

    用于生命周期管理
    """

    ACTIVE = "active"  # 当前活跃，可访问
    ARCHIVED = "archived"  # 已归档，可检索
    SUMMARIZED = "summarized"  # 已压缩为摘要
    EVICTED = "evicted"  # 已从活跃记忆中移除


@dataclass
class MemoryUnit:
    """
    记忆单元（Token-First Design）

    核心改动：
    - token_count: 必须字段，存储时计算
    - information_density: 信息密度评估（token 效率）
    """

    # 核心字段
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: Any = None
    tier: MemoryTier = MemoryTier.L2_WORKING
    type: MemoryType = MemoryType.MESSAGE

    # Token-First: 必须字段
    token_count: int = 0

    # 质量评估
    importance: float = 0.5  # 0.0-1.0
    information_density: float = 1.0  # token 效率（越高越好）

    # 溯源追踪
    source_node: str | None = None
    parent_id: str | None = None
    session_id: str | None = None

    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)

    # 扩展字段
    metadata: dict[str, Any] = field(default_factory=dict)

    # L4语义搜索
    embedding: list[float] | None = None

    # 生命周期状态
    status: MemoryStatus = MemoryStatus.ACTIVE

    def to_message(self) -> dict[str, str]:
        """
        转换为 LLM API 消息格式

        Returns:
            符合 LLM API 格式的消息字典
        """
        # 如果内容已经是消息格式，直接返回
        if isinstance(self.content, dict) and "role" in self.content:
            return self.content

        # 根据类型转换
        if self.type == MemoryType.MESSAGE:
            if isinstance(self.content, str):
                return {"role": "user", "content": self.content}
            if isinstance(self.content, dict):
                return {str(k): str(v) for k, v in self.content.items()}
            return {"role": "system", "content": str(self.content)}

        elif self.type == MemoryType.THOUGHT:
            return {"role": "assistant", "content": f"💭 {self.content}"}

        elif self.type == MemoryType.TOOL_CALL:
            return {"role": "assistant", "content": f"🔧 Tool Call: {self.content}"}

        elif self.type == MemoryType.TOOL_RESULT:
            return {"role": "system", "content": f"🔧 Tool Result: {self.content}"}

        elif self.type == MemoryType.PLAN:
            return {"role": "assistant", "content": f"📋 Plan: {self.content}"}

        elif self.type == MemoryType.FACT:
            return {"role": "system", "content": f"📚 Fact: {self.content}"}

        elif self.type == MemoryType.SUMMARY:
            return {"role": "system", "content": f"📝 Summary: {self.content}"}

        else:
            return {"role": "system", "content": str(self.content)}


@dataclass
class TaskSummary:
    """
    Task摘要 - 用于L3层存储

    将完整的Task对象压缩为摘要，减少存储开销
    """

    task_id: str
    action: str
    param_summary: str  # 参数摘要（而非完整参数）
    result_summary: str  # 结果摘要（而非完整结果）
    tags: list[str] = field(default_factory=list)
    importance: float = 0.5
    access_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    session_id: str | None = None


class FactType(Enum):
    """
    事实类型 - 用于分类可复用的原子知识

    基于优化分析文档的改进4
    """

    API_SCHEMA = "api_schema"  # API接口定义
    USER_PREFERENCE = "user_preference"  # 用户偏好
    DOMAIN_KNOWLEDGE = "domain_knowledge"  # 领域知识
    TOOL_USAGE = "tool_usage"  # 工具使用方法
    ERROR_PATTERN = "error_pattern"  # 错误模式
    BEST_PRACTICE = "best_practice"  # 最佳实践


@dataclass
class Fact:
    """
    可复用的事实 - 原子化知识存储

    从Task中提取的关键知识点，支持语义检索和复用。
    基于优化分析文档的改进4。
    """

    fact_id: str
    content: str  # 事实内容（简洁的文本描述）
    fact_type: FactType
    source_task_ids: list[str] = field(default_factory=list)  # 来源Task
    confidence: float = 0.8  # 置信度（0.0-1.0）
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0  # 访问次数（用于重要性评估）
    session_id: str | None = None

    def update_access(self) -> None:
        """更新访问信息"""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class MemoryQuery:
    """
    记忆查询请求
    """

    query: str
    tier: MemoryTier | None = None
    type: MemoryType | None = None
    limit: int = 10
    min_importance: float = 0.0
