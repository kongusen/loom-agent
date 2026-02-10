"""
Context Block - 上下文块数据结构

所有上下文的基本单位，携带 token 计数和优先级信息。
"""

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ContextBlock:
    """
    上下文块 - 所有上下文的基本单位

    设计原则：
    - Token-First: 每个块必须知道自己的 token 数
    - Priority-Based: 用于压缩时决定保留顺序
    - Source-Aware: 知道自己来自哪个源
    """

    content: str
    role: Literal["system", "user", "assistant"]
    token_count: int  # 必须字段，不是可选
    priority: float  # 0.0-1.0，越高越重要
    source: str  # "L1", "L2", "L3", "L4", "RAG", "INHERITED" 等

    # 可选字段
    compressible: bool = True  # 是否可压缩
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """验证字段"""
        if self.token_count < 0:
            raise ValueError("token_count must be non-negative")
        if not 0.0 <= self.priority <= 1.0:
            raise ValueError("priority must be between 0.0 and 1.0")

    def to_message(self) -> dict[str, str]:
        """转换为 LLM 消息格式"""
        return {"role": self.role, "content": self.content}

    def with_priority(self, new_priority: float) -> "ContextBlock":
        """返回新优先级的副本"""
        return ContextBlock(
            content=self.content,
            role=self.role,
            token_count=self.token_count,
            priority=new_priority,
            source=self.source,
            compressible=self.compressible,
            metadata=self.metadata.copy(),
        )

    def with_content(self, new_content: str, new_token_count: int) -> "ContextBlock":
        """返回新内容的副本（用于压缩后）"""
        return ContextBlock(
            content=new_content,
            role=self.role,
            token_count=new_token_count,
            priority=self.priority,
            source=self.source,
            compressible=self.compressible,
            metadata=self.metadata.copy(),
        )
