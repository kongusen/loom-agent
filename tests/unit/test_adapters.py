"""Tests for adapter modules — memory, knowledge, skills catalog."""

import pytest

from loom.knowledge.adapters import OrmGraphStoreAdapter, OrmVectorStoreAdapter
from loom.memory.adapters import VectorPersistentStore
from loom.types import MemoryEntry, SearchOptions

# ── Mock helpers ──

class _MockVectorStore:
    def __init__(self):
        self.data: dict[str, dict] = {}

    async def upsert(self, items):
        for it in items:
            self.data[it["id"]] = it

    async def query(self, vector, limit):
        return list(self.data.values())[:limit]

    async def delete(self, ids):
        for i in ids:
            self.data.pop(i, None)


class _MockEmbedder:
    async def embed(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


# ── VectorPersistentStore ──

class TestVectorPersistentStore:
    @pytest.fixture
    def store(self):
        return VectorPersistentStore(_MockVectorStore(), _MockEmbedder())

    async def test_save_and_search(self, store):
        entry = MemoryEntry(id="m1", content="hello", tokens=5, importance=0.8, metadata={}, created_at=1.0)
        await store.save(entry)
        hits = await store.search("hello", SearchOptions(limit=1))
        assert len(hits) == 1
        assert hits[0].id == "m1"

    async def test_delete(self, store):
        entry = MemoryEntry(id="m2", content="bye", tokens=3, importance=0.5, metadata={}, created_at=2.0)
        await store.save(entry)
        await store.delete("m2")
        hits = await store.search("bye", SearchOptions(limit=5))
        assert all(h.id != "m2" for h in hits)


# ── OrmVectorStoreAdapter ──

class TestOrmVectorStoreAdapter:
    @pytest.fixture
    def adapter(self):
        table: dict[str, dict] = {}

        async def add(id, vec, meta):
            table[id] = {"id": id, "vector": vec, "metadata": meta}

        async def search(vec, top_k):
            class Row:
                def __init__(self, d):
                    self.id, self.vector, self.metadata = d["id"], d["vector"], d["metadata"]
            return [Row(v) for v in list(table.values())[:top_k]]

        async def delete(ids):
            for i in ids:
                table.pop(i, None)

        def to_dict(row):
            return {"id": row.id, "content": row.metadata.get("c", "")}

        return OrmVectorStoreAdapter(add, search, delete, to_dict), table

    async def test_upsert_and_query(self, adapter):
        adp, table = adapter
        await adp.upsert([{"id": "a", "vector": [1.0], "metadata": {"c": "hi"}}])
        assert "a" in table
        results = await adp.query([1.0], 5)
        assert results[0]["id"] == "a"

    async def test_delete(self, adapter):
        adp, table = adapter
        await adp.upsert([{"id": "b", "vector": [1.0], "metadata": {}}])
        await adp.delete(["b"])
        assert "b" not in table


# ── OrmGraphStoreAdapter ──

class TestOrmGraphStoreAdapter:
    @pytest.fixture
    def adapter(self):
        entities: dict[str, dict] = {}
        relations: list[dict] = []

        async def add_entity(node):
            entities[node["id"]] = node

        async def add_relation(edge):
            relations.append(edge)

        async def find_related(query, limit):
            class E:
                def __init__(self, d):
                    self.id, self.name, self.type = d["id"], d.get("name", ""), d.get("type", "")
            return [E(e) for e in list(entities.values())[:limit]]

        async def get_neighbors(node_id, depth=1):
            class E:
                def __init__(self, d):
                    self.id, self.name, self.type = d["id"], d.get("name", ""), d.get("type", "")
            nids = set()
            for r in relations:
                if r.get("source") == node_id:
                    nids.add(r["target"])
            return [E(entities[n]) for n in nids if n in entities]

        def to_dict(e):
            return {"id": e.id, "name": e.name, "type": e.type}

        return OrmGraphStoreAdapter(add_entity, add_relation, find_related, get_neighbors, to_dict)

    async def test_add_nodes_and_find(self, adapter):
        await adapter.add_nodes([{"id": "x", "name": "X", "type": "t"}])
        results = await adapter.find_related("X", 5)
        assert results[0]["id"] == "x"

    async def test_edges_and_neighbors(self, adapter):
        await adapter.add_nodes([
            {"id": "a", "name": "A", "type": "t"},
            {"id": "b", "name": "B", "type": "t"},
        ])
        await adapter.add_edges([{"source": "a", "target": "b"}])
        neighbors = await adapter.get_neighbors("a")
        assert any(n["id"] == "b" for n in neighbors)
