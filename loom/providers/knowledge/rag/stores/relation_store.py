"""
关系存储接口和实现
"""

from abc import abstractmethod
from collections import deque

from loom.providers.knowledge.rag.models.relation import Relation
from loom.providers.knowledge.rag.stores.base import BaseStore


class RelationStore(BaseStore[Relation]):
    """
    关系存储接口

    提供关系的存储和图遍历能力
    """

    @abstractmethod
    async def get_by_entity(
        self,
        entity_id: str,
        direction: str = "both",
    ) -> list[Relation]:
        """
        获取实体的关系

        Args:
            entity_id: 实体ID
            direction: 方向 ("outgoing" | "incoming" | "both")

        Returns:
            关系列表
        """
        pass

    @abstractmethod
    async def get_n_hop(
        self,
        entity_id: str,
        n: int = 2,
        direction: str = "both",
    ) -> list[Relation]:
        """
        获取N跳范围内的关系

        Args:
            entity_id: 起始实体ID
            n: 跳数
            direction: 方向

        Returns:
            N跳范围内的所有关系
        """
        pass


class InMemoryRelationStore(RelationStore):
    """
    内存关系存储实现

    适用于开发测试和小规模数据
    """

    def __init__(self):
        self._relations: dict[str, Relation] = {}
        # 邻接表索引
        self._outgoing: dict[str, set[str]] = {}  # source_id -> relation_ids
        self._incoming: dict[str, set[str]] = {}  # target_id -> relation_ids

    async def add(self, relation: Relation) -> None:
        """添加关系"""
        self._relations[relation.id] = relation
        # 更新邻接表
        if relation.source_id not in self._outgoing:
            self._outgoing[relation.source_id] = set()
        self._outgoing[relation.source_id].add(relation.id)

        if relation.target_id not in self._incoming:
            self._incoming[relation.target_id] = set()
        self._incoming[relation.target_id].add(relation.id)

    async def add_batch(self, relations: list[Relation]) -> None:
        """批量添加"""
        for relation in relations:
            await self.add(relation)

    async def get(self, relation_id: str) -> Relation | None:
        """根据ID获取"""
        return self._relations.get(relation_id)

    async def get_by_ids(self, relation_ids: list[str]) -> list[Relation]:
        """批量获取"""
        return [self._relations[rid] for rid in relation_ids if rid in self._relations]

    async def delete(self, relation_id: str) -> bool:
        """删除"""
        if relation_id in self._relations:
            relation = self._relations.pop(relation_id)
            if relation.source_id in self._outgoing:
                self._outgoing[relation.source_id].discard(relation_id)
            if relation.target_id in self._incoming:
                self._incoming[relation.target_id].discard(relation_id)
            return True
        return False

    async def clear(self) -> None:
        """清空"""
        self._relations.clear()
        self._outgoing.clear()
        self._incoming.clear()

    async def get_by_entity(
        self,
        entity_id: str,
        direction: str = "both",
    ) -> list[Relation]:
        """获取实体的关系"""
        relation_ids: set[str] = set()
        if direction in ("outgoing", "both"):
            relation_ids.update(self._outgoing.get(entity_id, set()))
        if direction in ("incoming", "both"):
            relation_ids.update(self._incoming.get(entity_id, set()))
        return await self.get_by_ids(list(relation_ids))

    async def get_n_hop(
        self,
        entity_id: str,
        n: int = 2,
        direction: str = "both",
    ) -> list[Relation]:
        """BFS 获取 N 跳范围内的关系"""
        visited_entities: set[str] = set()
        visited_relations: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(entity_id, 0)])

        while queue:
            current_id, depth = queue.popleft()
            if depth >= n:
                continue
            if current_id in visited_entities:
                continue
            visited_entities.add(current_id)

            relations = await self.get_by_entity(current_id, direction)
            for rel in relations:
                if rel.id not in visited_relations:
                    visited_relations.add(rel.id)
                    # 添加邻居到队列
                    next_id = rel.target_id if rel.source_id == current_id else rel.source_id
                    if next_id not in visited_entities:
                        queue.append((next_id, depth + 1))

        return await self.get_by_ids(list(visited_relations))
