# Knowledge

KnowledgeBase 提供 RAG（检索增强生成）能力：文档摄入、分块、向量化、混合检索（关键词 + 向量 RRF 融合）。

## 创建知识库

```python
from loom import KnowledgeBase, Document
from loom.knowledge import InMemoryVectorStore

kb = KnowledgeBase(
    embedder=embedder,                    # EmbeddingProvider 实现
    vector_store=InMemoryVectorStore(),   # 向量存储
)
```

## 文档摄入

```python
await kb.ingest([
    Document(id="d1", content="Python 是通用编程语言，适合数据科学和 Web 开发"),
    Document(id="d2", content="Rust 是系统级编程语言，注重安全和性能"),
    Document(id="d3", content="Python 的 asyncio 库支持异步编程模式"),
])
```

## 混合检索

`query()` 同时执行关键词匹配和向量相似度搜索，通过 RRF（Reciprocal Rank Fusion）融合排序：

```python
results = await kb.query("Python 编程")
for r in results:
    print(f"[{r.chunk.id}] score={r.score:.3f} — {r.chunk.content[:40]}")
# [d1_c0] score=1.000 — Python 是通用编程语言...
# [d3_c0] score=0.500 — Python 的 asyncio 库...
# [d2_c0] score=0.200 — Rust 是系统级编程语言...
```

## 接入 Agent

知识库本身只负责存储和检索，要让 Agent 在对话时自动获取相关知识，需要通过 `KnowledgeProvider` → `ContextOrchestrator` → `Agent` 三步桥接：

```python
from loom import (
    Agent, AgentConfig, ContextOrchestrator, KnowledgeProvider,
)

# 1. 用 KnowledgeProvider 包装知识库
kp = KnowledgeProvider(kb)

# 2. 注册到 ContextOrchestrator
context = ContextOrchestrator()
context.register(kp)

# 3. 注入 Agent
agent = Agent(
    provider=provider,
    config=AgentConfig(max_steps=2),
    context=context,
)

# Agent 对话时自动检索知识库，注入相关文档片段到 LLM 上下文
result = await agent.run("Loom 框架的记忆系统有哪些层级？")
```

**工作流程：** 用户提问 → ContextOrchestrator 调用 KnowledgeProvider → KnowledgeProvider 调用 `kb.query()` 检索相关文档 → 检索结果作为上下文片段注入 LLM 消息 → LLM 基于注入的知识回答。

无 Context 时 LLM 只能泛泛而谈；有 Context 后 LLM 能给出基于文档的准确回答。

> 详见 [Context 编排](Context) 了解 ContextOrchestrator 的完整用法，完整示例：[`examples/demo/07_context.py`](../examples/demo/07_context.py)

## EmbeddingProvider 协议

自定义 embedder 需实现：

```python
class MyEmbedder:
    async def embed(self, text: str) -> list[float]: ...
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
```

## API 参考

```python
kb = KnowledgeBase(embedder=..., vector_store=..., chunker=...)
await kb.ingest(documents: list[Document])
await kb.query(query: str, options: RetrieverOptions = None) -> list[RetrievalResult]

# 分块器
FixedSizeChunker(chunk_size=512)
RecursiveChunker(chunk_size=512)
```

> 完整示例：[`examples/demo/06_knowledge.py`](../examples/demo/06_knowledge.py)
