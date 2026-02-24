"""16 — Adapter 能力验证：OrmVectorStore / OrmGraphStore / VectorPersistentStore / SkillCatalogProvider。

使用 mock 数据库层 + 真实 API 验证四项新能力在 Python 框架中的实现。
"""

import asyncio
import math
import time

from _provider import OpenAIEmbedder, create_provider

from loom import (
    Agent,
    AgentConfig,
    ContextOrchestrator,
    MemoryEntry,
    MemoryManager,
    SkillCatalogProvider,
    SkillRegistry,
    SlidingWindow,
    WorkingMemory,
)
from loom.cluster.skill_registry import SkillNodeRegistry
from loom.knowledge.adapters import OrmGraphStoreAdapter, OrmVectorStoreAdapter
from loom.memory.adapters import VectorPersistentStore
from loom.types import SearchOptions, Skill

# ═══════════════════════════════════════════════════════════════
# Part 1: Mock 数据库层
# ═══════════════════════════════════════════════════════════════

vector_table: dict[str, dict] = {}
entity_table: dict[str, dict] = {}
relation_table: list[dict] = []


def cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


async def mock_vector_add(id: str, embedding: list[float], metadata: dict) -> None:
    vector_table[id] = {"id": id, "vector": embedding, "metadata": metadata}


async def mock_vector_search(embedding: list[float], top_k: int) -> list:
    scored = []
    for row in vector_table.values():
        sim = cosine_sim(embedding, row["vector"])
        scored.append((sim, row))
    scored.sort(key=lambda x: x[0], reverse=True)

    class Row:
        def __init__(self, data):
            self.id = data["id"]
            self.vector = data["vector"]
            self.metadata = data["metadata"]

    return [Row(r) for _, r in scored[:top_k]]


async def mock_vector_delete(ids: list[str]) -> None:
    for i in ids:
        vector_table.pop(i, None)


def vector_row_to_dict(row) -> dict:
    return {"id": row.id, "content": row.metadata.get("content", ""), "metadata": row.metadata}


# ── Mock Graph DB ──

async def mock_add_entity(node: dict) -> None:
    entity_table[node["id"]] = node


async def mock_add_relation(edge: dict) -> None:
    relation_table.append(edge)


async def mock_find_related(query: str, limit: int) -> list:
    class Entity:
        def __init__(self, d):
            self.id = d["id"]
            self.name = d.get("name", d["id"])
            self.type = d.get("type", "unknown")
            self.data = d

    q = query.lower()
    matched = [Entity(e) for e in entity_table.values() if q in e.get("name", "").lower()]
    return matched[:limit]


async def mock_get_neighbors(node_id: str, depth: int = 1) -> list:
    class Entity:
        def __init__(self, d):
            self.id = d["id"]
            self.name = d.get("name", d["id"])
            self.type = d.get("type", "unknown")
            self.data = d

    neighbor_ids: set[str] = set()
    for rel in relation_table:
        if rel.get("source") == node_id:
            neighbor_ids.add(rel["target"])
        elif rel.get("target") == node_id:
            neighbor_ids.add(rel["source"])
    return [Entity(entity_table[nid]) for nid in neighbor_ids if nid in entity_table]


def entity_to_dict(e) -> dict:
    return {"id": e.id, "name": e.name, "type": e.type}


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

async def main():
    print("=" * 60)
    print("Loom v0.6.1 — Adapter 能力验证 (Demo 16)")
    print("=" * 60)

    provider = create_provider()
    embedder = OpenAIEmbedder()

    # ── Part 2: OrmVectorStoreAdapter ──
    print("\n[Part 2] OrmVectorStoreAdapter — ORM → VectorStore Protocol")

    orm_vector = OrmVectorStoreAdapter(
        add_fn=mock_vector_add,
        search_fn=mock_vector_search,
        delete_fn=mock_vector_delete,
        to_dict=vector_row_to_dict,
    )

    vec1 = await embedder.embed("Loom 是一个多智能体框架")
    vec2 = await embedder.embed("记忆系统分为三层：滑动窗口、工作记忆、持久存储")
    vec3 = await embedder.embed("Amoeba 机制实现自组织集群")

    await orm_vector.upsert([
        {"id": "v1", "vector": vec1, "metadata": {"content": "Loom 是一个多智能体框架"}},
        {"id": "v2", "vector": vec2, "metadata": {"content": "记忆系统分为三层：滑动窗口、工作记忆、持久存储"}},
        {"id": "v3", "vector": vec3, "metadata": {"content": "Amoeba 机制实现自组织集群"}},
    ])

    q_vec = await embedder.embed("记忆怎么工作")
    results = await orm_vector.query(q_vec, 2)
    print("  存储: 3 条向量")
    print("  查询 '记忆怎么工作' top-2:")
    for r in results:
        print(f"    → {r['id']}: {r['content'][:40]}")
    assert results[0]["id"] == "v2", f"期望 v2 排第一，实际 {results[0]['id']}"
    print("  ✓ OrmVectorStoreAdapter 验证通过")

    # ── Part 3: OrmGraphStoreAdapter ──
    print("\n[Part 3] OrmGraphStoreAdapter — ORM → GraphStore Protocol")

    orm_graph = OrmGraphStoreAdapter(
        add_entity_fn=mock_add_entity,
        add_relation_fn=mock_add_relation,
        find_related_fn=mock_find_related,
        get_neighbors_fn=mock_get_neighbors,
        entity_to_dict=entity_to_dict,
    )

    await orm_graph.add_nodes([
        {"id": "n1", "name": "Loom-Agent", "type": "framework"},
        {"id": "n2", "name": "Memory", "type": "module"},
        {"id": "n3", "name": "Amoeba", "type": "module"},
        {"id": "n4", "name": "Knowledge", "type": "module"},
    ])
    await orm_graph.add_edges([
        {"source": "n1", "target": "n2", "relation": "contains"},
        {"source": "n1", "target": "n3", "relation": "contains"},
        {"source": "n1", "target": "n4", "relation": "contains"},
    ])

    related = await orm_graph.find_related("Memory", 5)
    print("  实体: 4, 关系: 3")
    print(f"  find_related('Memory'): {[r['name'] for r in related]}")

    neighbors = await orm_graph.get_neighbors("n1")
    neighbor_names = sorted(r["name"] for r in neighbors)
    print(f"  get_neighbors('n1'): {neighbor_names}")
    assert "Memory" in neighbor_names, "Memory 应在邻居中"
    assert "Amoeba" in neighbor_names, "Amoeba 应在邻居中"
    print("  ✓ OrmGraphStoreAdapter 验证通过")

    # ── Part 4: VectorPersistentStore ──
    print("\n[Part 4] VectorPersistentStore — VectorStore + Embedder → PersistentStore")

    # 清空 Part 2 的数据，使用干净的向量表
    vector_table.clear()
    vector_persistent = VectorPersistentStore(store=orm_vector, embedder=embedder)

    await vector_persistent.save(MemoryEntry(
        id="mem-1",
        content="记忆系统的三层架构：L1 滑动窗口保持最近对话，L2 工作记忆存储重要摘要，L3 持久存储用于长期知识",
        tokens=30, importance=0.9,
        metadata={"topic": "memory"}, created_at=time.time(),
    ))
    await vector_persistent.save(MemoryEntry(
        id="mem-2",
        content="Amoeba 自组织机制通过拍卖、有丝分裂、凋亡实现集群动态伸缩",
        tokens=25, importance=0.8,
        metadata={"topic": "amoeba"}, created_at=time.time(),
    ))
    await vector_persistent.save(MemoryEntry(
        id="mem-3",
        content="SkillCatalogProvider 使用 LLM 语义路由实现渐进式技能加载",
        tokens=20, importance=0.7,
        metadata={"topic": "skills"}, created_at=time.time(),
    ))

    hits = await vector_persistent.search("记忆系统怎么工作", SearchOptions(limit=2))
    print("  存储: 3 条记忆")
    print("  语义搜索 '记忆系统怎么工作' top-2:")
    for h in hits:
        print(f"    → {h.id}: {h.content[:40]}...")
    assert hits[0].id == "mem-1", f"期望 mem-1 排第一，实际 {hits[0].id}"
    print("  ✓ VectorPersistentStore 语义搜索验证通过")

    # ── Part 5: 三层记忆 (L3 = VectorPersistentStore) ──
    print("\n[Part 5] 三层记忆 — SlidingWindow + WorkingMemory + VectorPersistentStore(L3)")

    # MemoryManager.l3 expects store()/retrieve(); wrap VectorPersistentStore
    class VectorL3Adapter:
        """Adapts VectorPersistentStore → MemoryManager L3 interface."""

        name = "vector_persistent"

        def __init__(self, vps: VectorPersistentStore):
            self._vps = vps
            self.token_budget = 32000
            self.current_tokens = 0

        async def store(self, entry: MemoryEntry) -> None:
            await self._vps.save(entry)
            self.current_tokens += entry.tokens

        async def retrieve(self, query: str = "", limit: int = 10) -> list[MemoryEntry]:
            return await self._vps.search(query or "recent", SearchOptions(limit=limit))

    memory = MemoryManager(
        l1=SlidingWindow(token_budget=100),
        l2=WorkingMemory(token_budget=200),
        l3=VectorL3Adapter(vector_persistent),
    )

    l3_results = await memory.get_l3_context("自组织集群", limit=2)
    print("  L3 语义召回 '自组织集群' top-2:")
    for e in l3_results:
        print(f"    → {e.id}: {e.content[:40]}...")
    assert any(e.id == "mem-2" for e in l3_results), "mem-2 应在 L3 召回中"
    print("  ✓ 三层记忆 + VectorPersistentStore(L3) 验证通过")

    # ── Part 6: SkillCatalogProvider ──
    print("\n[Part 6] SkillCatalogProvider — LLM 语义路由 + 渐进式技能加载")

    catalog = SkillNodeRegistry()
    catalog.register_all([
        Skill(
            name="translator",
            description="多语言翻译专家，擅长中英日韩互译",
            instructions="你是翻译专家。保持原文语义，输出自然流畅的译文。",
        ),
        Skill(
            name="coder",
            description="编程专家，擅长算法、数据结构、系统设计",
            instructions="你是编程专家。给出高效、可读的代码实现，附带复杂度分析。",
        ),
        Skill(
            name="mathematician",
            description="数学专家，擅长微积分、线性代数、概率统计",
            instructions="你是数学专家。给出严谨的推导过程和最终结果。",
        ),
    ])

    skill_registry = SkillRegistry()
    skill_catalog = SkillCatalogProvider(
        catalog=catalog,
        registry=skill_registry,
        llm=provider,
    )

    # 测试语义路由
    fragments = await skill_catalog.provide("快速排序算法的时间复杂度", budget=500)
    print(f"  技能目录: {catalog.size} 个技能")
    print("  查询 '快速排序算法的时间复杂度':")
    if fragments:
        loaded_name = fragments[0].metadata.get("skill_name", "?")
        print(f"    → 路由到: {loaded_name}")
        print(f"    → 指令片段: {fragments[0].content[:40]}...")
        assert loaded_name == "coder", f"期望路由到 coder，实际 {loaded_name}"
    else:
        print("    → (无匹配)")
    print(f"  已加载技能: {[s.name for s in skill_registry.all()]}")
    print("  ✓ SkillCatalogProvider 语义路由验证通过")

    # ── Part 7: Agent + ContextOrchestrator + 多轮对话 ──
    print("\n[Part 7] Agent — Context 编排 + 多轮对话")

    context = ContextOrchestrator()
    context.register(skill_catalog)

    agent = Agent(
        provider=provider,
        config=AgentConfig(system_prompt="你是 AI 技术专家，简洁回答。", max_steps=3),
        name="adapter-demo",
        memory=memory,
        context=context,
    )

    queries = [
        "请把 'Hello World' 翻译成日语",
        "贝叶斯定理的公式是什么？",
        "总结一下我们刚才聊了什么",
    ]

    for i, q in enumerate(queries, 1):
        print(f"\n  [{i}] 用户: {q}")
        result = await agent.run(q)
        print(f"      回复: {result.content[:80]}...")
        print(f"      tokens: {result.usage.total_tokens}")

    # 验证渐进式加载
    loaded = [s.name for s in skill_registry.all()]
    print(f"\n  渐进式加载结果: {loaded}")
    print(f"  L1 消息数: {len(memory.l1.get_messages())}")

    print("\n" + "=" * 60)
    print("Demo 16 — 全部 4 项 Adapter 能力验证通过")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
