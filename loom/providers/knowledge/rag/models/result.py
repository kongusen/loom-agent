"""
检索结果数据模型
"""

from dataclasses import dataclass, field

from loom.providers.knowledge.rag.models.chunk import TextChunk
from loom.providers.knowledge.rag.models.entity import Entity
from loom.providers.knowledge.rag.models.relation import Relation


@dataclass
class RetrievalResult:
    """
    检索结果 - 封装完整的检索输出

    Attributes:
        chunks: 检索到的文本块列表
        entities: 相关实体列表
        relations: 相关关系列表
        scores: chunk_id -> 相关度分数的映射
    """

    chunks: list[TextChunk] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)

    def is_empty(self) -> bool:
        """检查结果是否为空"""
        return len(self.chunks) == 0

    def get_top_chunks(self, n: int = 5) -> list[TextChunk]:
        """获取得分最高的 N 个文本块"""
        sorted_chunks = sorted(
            self.chunks,
            key=lambda c: self.scores.get(c.id, 0.0),
            reverse=True,
        )
        return sorted_chunks[:n]
