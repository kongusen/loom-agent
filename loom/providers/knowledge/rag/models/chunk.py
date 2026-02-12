"""
文本块数据模型
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TextChunk:
    """
    文本块 - RAG 系统的基本检索单元

    Attributes:
        id: 唯一标识符
        content: 文本内容
        document_id: 所属文档ID
        embedding: 向量表示（可选）
        entity_ids: 关联的实体ID列表
        keywords: 关键词列表
        metadata: 附加元数据
    """

    id: str
    content: str
    document_id: str
    embedding: list[float] | None = None
    entity_ids: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """验证必填字段"""
        if not self.id:
            raise ValueError("TextChunk.id cannot be empty")
        if not self.content:
            raise ValueError("TextChunk.content cannot be empty")
