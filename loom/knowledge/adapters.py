"""Adapters — bridge ORM-based stores to dict-based VectorStore/GraphStore Protocols."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


class OrmVectorStoreAdapter:
    """Adapts any ORM chunk store → VectorStore Protocol.

    Usage:
        adapter = OrmVectorStoreAdapter(
            add_fn=pg_chunk_store.add,        # (id, embedding, metadata) -> None
            search_fn=pg_chunk_store.search,   # (embedding, top_k) -> list[OrmObj]
            delete_fn=pg_chunk_store.delete,   # (ids) -> None
            to_dict=lambda obj: {"id": obj.id, "content": obj.text, ...},
        )
    """

    def __init__(
        self,
        add_fn: Callable[..., Awaitable[None]],
        search_fn: Callable[..., Awaitable[list]],
        delete_fn: Callable[..., Awaitable[None]],
        to_dict: Callable[[Any], dict[str, Any]],
    ) -> None:
        self._add = add_fn
        self._search = search_fn
        self._delete = delete_fn
        self._to_dict = to_dict

    async def upsert(self, items: list[dict[str, Any]]) -> None:
        for item in items:
            await self._add(item["id"], item.get("vector", []), item.get("metadata", {}))

    async def query(self, vector: list[float], limit: int) -> list[dict[str, Any]]:
        results = await self._search(vector, limit)
        return [self._to_dict(r) for r in results]

    async def delete(self, ids: list[str]) -> None:
        await self._delete(ids)


class OrmGraphStoreAdapter:
    """Adapts ORM entity+relation stores → GraphStore Protocol.

    Usage:
        adapter = OrmGraphStoreAdapter(
            add_entity_fn=entity_store.add,
            add_relation_fn=relation_store.add,
            find_related_fn=entity_store.search,
            get_neighbors_fn=relation_store.get_neighbors,
            entity_to_dict=lambda e: {"id": e.id, "content": e.name, ...},
        )
    """

    def __init__(
        self,
        add_entity_fn: Callable[..., Awaitable[None]],
        add_relation_fn: Callable[..., Awaitable[None]],
        find_related_fn: Callable[..., Awaitable[list]],
        get_neighbors_fn: Callable[..., Awaitable[list]],
        entity_to_dict: Callable[[Any], dict[str, Any]],
    ) -> None:
        self._add_entity = add_entity_fn
        self._add_relation = add_relation_fn
        self._find_related = find_related_fn
        self._get_neighbors = get_neighbors_fn
        self._to_dict = entity_to_dict

    async def add_nodes(self, nodes: list[dict[str, Any]]) -> None:
        for n in nodes:
            await self._add_entity(n)

    async def add_edges(self, edges: list[dict[str, Any]]) -> None:
        for e in edges:
            await self._add_relation(e)

    async def find_related(self, query: str, limit: int) -> list[dict[str, Any]]:
        results = await self._find_related(query, limit)
        return [self._to_dict(r) for r in results]

    async def get_neighbors(self, node_id: str, depth: int = 1) -> list[dict[str, Any]]:
        results = await self._get_neighbors(node_id, depth)
        return [self._to_dict(r) for r in results]
