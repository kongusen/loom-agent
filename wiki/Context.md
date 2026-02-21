# Context

ContextOrchestrator 自动从多个来源收集上下文片段，注入到 LLM 调用中，让 Agent 具备领域知识。

## 基础用法

```python
from loom import (
    Agent, AgentConfig, ContextOrchestrator,
    KnowledgeBase, KnowledgeProvider, Document,
)
from loom.knowledge import InMemoryVectorStore

# 1. 构建知识库
kb = KnowledgeBase(embedder=embedder, vector_store=InMemoryVectorStore())
await kb.ingest([
    Document(id="d1", content="Loom 记忆分三层：L1 SlidingWindow、L2 WorkingMemory、L3 PersistentStore"),
])

# 2. 注册到 ContextOrchestrator
context = ContextOrchestrator()
context.register(KnowledgeProvider(kb))

# 3. 注入 Agent
agent = Agent(
    provider=provider,
    config=AgentConfig(max_steps=2),
    context=context,
)
```

## 效果对比

```python
# 无 Context — LLM 不了解 Loom 框架
agent1 = Agent(provider=provider)
r1 = await agent1.run("Loom 框架的记忆系统有哪些层级？")
# → 泛泛而谈，不准确

# 有 Context — 知识库自动注入
agent2 = Agent(provider=provider, context=context)
r2 = await agent2.run("Loom 框架的记忆系统有哪些层级？")
# → "L1 SlidingWindow、L2 WorkingMemory、L3 PersistentStore"
```

## 自定义 ContextProvider

```python
from loom import ContextProvider, ContextFragment

class MyProvider(ContextProvider):
    name = "custom"
    async def gather(self, query, budget) -> list[ContextFragment]:
        return [ContextFragment(content="自定义上下文", source=self.name)]
```

## API 参考

```python
context = ContextOrchestrator()
context.register(provider: ContextProvider)
# 内置 Provider
KnowledgeProvider(kb)          # 从知识库检索
MemoryContextProvider(memory)  # 从记忆层提取
MitosisContextProvider(...)    # 从分裂上下文提取
```

> 完整示例：[`examples/demo/07_context.py`](../examples/demo/07_context.py)
