"""
实体存储接口和实现
"""

from abc import abstractmethod

from loom.providers.knowledge.rag.models.entity import Entity
from loom.providers.knowledge.rag.stores.base import BaseStore


class EntityStore(BaseStore[Entity]):
    """
    实体存储接口

    提供实体的存储和检索能力
    """

    @abstractmethod
    async def get_by_text(self, text: str) -> Entity | None:
        """
        根据实体文本获取

        Args:
            text: 实体文本

        Returns:
            匹配的实体，不存在则返回 None
        """
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        entity_type: str | None = None,
        limit: int = 10,
    ) -> list[Entity]:
        """
        搜索实体

        Args:
            query: 搜索文本
            entity_type: 实体类型过滤
            limit: 返回数量限制

        Returns:
            匹配的实体列表
        """
        pass

    @abstractmethod
    async def get_by_chunk(self, chunk_id: str) -> list[Entity]:
        """
        获取文本块关联的实体

        Args:
            chunk_id: 文本块ID

        Returns:
            关联的实体列表
        """
        pass


class InMemoryEntityStore(EntityStore):
    """
    内存实体存储实现

    适用于开发测试和小规模数据
    """

    def __init__(self):
        self._entities: dict[str, Entity] = {}
        self._text_index: dict[str, str] = {}  # text -> entity_id
        self._chunk_index: dict[str, set[str]] = {}  # chunk_id -> entity_ids

    async def add(self, entity: Entity) -> None:
        """添加实体"""
        self._entities[entity.id] = entity
        self._text_index[entity.text.lower()] = entity.id
        # 更新 chunk 索引
        for chunk_id in entity.chunk_ids:
            if chunk_id not in self._chunk_index:
                self._chunk_index[chunk_id] = set()
            self._chunk_index[chunk_id].add(entity.id)

    async def add_batch(self, entities: list[Entity]) -> None:
        """批量添加"""
        for entity in entities:
            await self.add(entity)

    async def get(self, entity_id: str) -> Entity | None:
        """根据ID获取"""
        return self._entities.get(entity_id)

    async def get_by_ids(self, entity_ids: list[str]) -> list[Entity]:
        """批量获取"""
        return [self._entities[eid] for eid in entity_ids if eid in self._entities]

    async def delete(self, entity_id: str) -> bool:
        """删除"""
        if entity_id in self._entities:
            entity = self._entities.pop(entity_id)
            self._text_index.pop(entity.text.lower(), None)
            for chunk_id in entity.chunk_ids:
                if chunk_id in self._chunk_index:
                    self._chunk_index[chunk_id].discard(entity_id)
            return True
        return False

    async def clear(self) -> None:
        """清空"""
        self._entities.clear()
        self._text_index.clear()
        self._chunk_index.clear()

    async def get_by_text(self, text: str) -> Entity | None:
        """根据实体文本获取"""
        entity_id = self._text_index.get(text.lower())
        if entity_id:
            return self._entities.get(entity_id)
        return None

    async def search(
        self,
        query: str,
        entity_type: str | None = None,
        limit: int = 10,
    ) -> list[Entity]:
        """搜索实体"""
        query_lower = query.lower()
        matches = []
        for entity in self._entities.values():
            if entity_type and entity.entity_type != entity_type:
                continue
            if query_lower in entity.text.lower():
                matches.append(entity)
        # 按频率排序
        matches.sort(key=lambda e: e.frequency, reverse=True)
        return matches[:limit]

    async def get_by_chunk(self, chunk_id: str) -> list[Entity]:
        """获取文本块关联的实体"""
        entity_ids = self._chunk_index.get(chunk_id, set())
        return await self.get_by_ids(list(entity_ids))
