"""
关系数据模型
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Relation:
    """
    知识图谱关系

    Attributes:
        id: 唯一标识符
        source_id: 源实体ID
        target_id: 目标实体ID
        relation_type: 关系类型
        description: 关系描述
        weight: 关系权重
        chunk_id: 来源文本块ID
        metadata: 附加元数据
    """

    id: str
    source_id: str
    target_id: str
    relation_type: str
    description: str | None = None
    weight: float = 1.0
    chunk_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Relation):
            return self.id == other.id
        return False
