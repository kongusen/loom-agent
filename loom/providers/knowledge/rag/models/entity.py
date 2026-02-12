"""
实体数据模型
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Entity:
    """
    知识图谱实体

    Attributes:
        id: 唯一标识符
        text: 实体文本（名称）
        entity_type: 实体类型（如 PERSON, ORG, CONCEPT 等）
        description: 实体描述
        chunk_ids: 关联的文本块ID列表
        frequency: 出现频率
        metadata: 附加元数据
    """

    id: str
    text: str
    entity_type: str
    description: str | None = None
    chunk_ids: list[str] = field(default_factory=list)
    frequency: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Entity):
            return self.id == other.id
        return False
