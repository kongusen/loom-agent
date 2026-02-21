"""06 — 知识库 RAG：文档摄入、关键词+向量混合检索（RRF 融合）。"""

import asyncio
from loom import KnowledgeBase, Document
from loom.knowledge import InMemoryVectorStore
from _provider import OpenAIEmbedder


async def main():
    kb = KnowledgeBase(
        embedder=OpenAIEmbedder(),
        vector_store=InMemoryVectorStore(),
    )

    # ── 1. 摄入文档 ──
    print("[1] 摄入文档")
    await kb.ingest([
        Document(id="d1", content="Python 是一门通用编程语言，适合数据科学和 Web 开发"),
        Document(id="d2", content="Rust 是系统级编程语言，注重安全和性能"),
        Document(id="d3", content="Python 的 asyncio 库支持异步编程模式"),
    ])
    print("  摄入 3 篇文档")

    # ── 2. 混合检索 ──
    print("\n[2] 混合检索 (关键词 + 向量 RRF)")
    results = await kb.query("Python 编程")
    for r in results:
        print(f"  [{r.chunk.id}] score={r.score:.3f} — {r.chunk.content[:40]}")

    # ── 3. 不相关查询 ──
    print("\n[3] 查询 'Java'")
    results2 = await kb.query("Java 框架")
    print(f"  结果数: {len(results2)}")
    for r in results2:
        print(f"  [{r.chunk.id}] score={r.score:.3f} — {r.chunk.content[:40]}")


if __name__ == "__main__":
    asyncio.run(main())
