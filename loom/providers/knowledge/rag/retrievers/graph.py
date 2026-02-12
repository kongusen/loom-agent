"""
图检索器
"""

from typing import Any

from loom.providers.knowledge.rag.models.chunk import TextChunk
from loom.providers.knowledge.rag.models.entity import Entity
from loom.providers.knowledge.rag.models.relation import Relation
from loom.providers.knowledge.rag.retrievers.base import BaseRetriever
from loom.providers.knowledge.rag.stores.chunk_store import ChunkStore
from loom.providers.knowledge.rag.stores.entity_store import EntityStore
from loom.providers.knowledge.rag.stores.relation_store import RelationStore


class GraphRetriever(BaseRetriever):
    """
    图检索器

    基于知识图谱进行结构化检索：
    1. 实体识别 - 从查询中匹配实体
    2. N跳遍历 - 获取相关实体和关系
    3. 定位Chunk - 找到关联的文本块
    """

    def __init__(
        self,
        entity_store: EntityStore,
        relation_store: RelationStore,
        chunk_store: ChunkStore,
    ):
        self.entity_store = entity_store
        self.relation_store = relation_store
        self.chunk_store = chunk_store

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        n_hop: int = 2,
        **_kwargs: Any,
    ) -> tuple[list[Entity], list[Relation], list[TextChunk]]:
        """
        图检索

        Args:
            query: 查询文本
            limit: 返回数量限制
            n_hop: 图遍历跳数

        Returns:
            (entities, relations, chunks) 三元组
        """
        # 1. 实体识别（从查询中匹配实体）
        seed_entities = await self.entity_store.search(query, limit=5)

        if not seed_entities:
            return [], [], []

        # 2. N跳关系遍历
        all_relations: list[Relation] = []
        visited_entity_ids: set[str] = set()

        for entity in seed_entities:
            relations = await self.relation_store.get_n_hop(
                entity.id, n=n_hop
            )
            all_relations.extend(relations)
            visited_entity_ids.add(entity.id)

            # 收集关联实体ID
            for rel in relations:
                visited_entity_ids.add(rel.source_id)
                visited_entity_ids.add(rel.target_id)

        # 3. 获取所有相关实体
        all_entities = await self.entity_store.get_by_ids(
            list(visited_entity_ids)
        )

        # 4. 定位关联的Chunk
        chunk_ids: set[str] = set()
        for entity in all_entities:
            chunk_ids.update(entity.chunk_ids)

        chunks = await self.chunk_store.get_by_ids(list(chunk_ids)[:limit])

        # 去重关系
        unique_relations = list({r.id: r for r in all_relations}.values())

        return all_entities, unique_relations, chunks
