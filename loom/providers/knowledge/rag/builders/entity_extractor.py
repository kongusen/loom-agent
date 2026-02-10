"""
实体抽取器
"""

import re
import uuid
from abc import ABC, abstractmethod

from loom.providers.knowledge.rag.models.chunk import TextChunk
from loom.providers.knowledge.rag.models.entity import Entity
from loom.providers.knowledge.rag.models.relation import Relation


class EntityExtractor(ABC):
    """实体抽取器抽象接口"""

    @abstractmethod
    async def extract(
        self,
        chunk: TextChunk,
    ) -> tuple[list[Entity], list[Relation]]:
        """
        从文本块中抽取实体和关系

        Args:
            chunk: 文本块

        Returns:
            (entities, relations) 元组
        """
        pass


class SimpleEntityExtractor(EntityExtractor):
    """
    简单实体抽取器

    基于规则的实体抽取，适用于快速原型
    实际生产环境建议使用 LLM 或 NER 模型
    """

    def __init__(
        self,
        patterns: dict[str, str] | None = None,
    ):
        """
        初始化

        Args:
            patterns: 实体类型 -> 正则表达式的映射
        """
        self.patterns = patterns or {
            "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "URL": r"https?://[^\s]+",
            "PHONE": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        }

    async def extract(
        self,
        chunk: TextChunk,
    ) -> tuple[list[Entity], list[Relation]]:
        """基于正则的实体抽取"""
        entities = []
        content = chunk.content

        for entity_type, pattern in self.patterns.items():
            matches = re.findall(pattern, content)
            for match in matches:
                entity_id = f"entity_{uuid.uuid4().hex[:8]}"
                entities.append(
                    Entity(
                        id=entity_id,
                        text=match,
                        entity_type=entity_type,
                        chunk_ids=[chunk.id],
                    )
                )

        # 简单实现不抽取关系
        return entities, []
