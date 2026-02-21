"""07 — Context 编排器：自动注入知识上下文，增强 LLM 回答准确性。"""

import asyncio
from loom import (
    Agent, AgentConfig, ContextOrchestrator,
    KnowledgeBase, KnowledgeProvider, Document,
)
from loom.knowledge import InMemoryVectorStore
from _provider import create_provider, OpenAIEmbedder


async def main():
    provider = create_provider()
    question = "Loom 框架的记忆系统有哪些层级？"

    # ── 1. 无 Context — LLM 不了解 Loom 框架 ──
    print("[1] 无 Context (LLM 缺乏领域知识)")
    agent1 = Agent(provider=provider, config=AgentConfig(max_steps=2))
    r1 = await agent1.run(question)
    print(f"  回复: {r1.content[:120]}...")

    # ── 2. 有 Context — 知识库自动注入相关文档 ──
    print("\n[2] Context + KnowledgeProvider (自动注入)")
    kb = KnowledgeBase(embedder=OpenAIEmbedder(), vector_store=InMemoryVectorStore())
    await kb.ingest([
        Document(id="d1", content="Loom 记忆系统分三层：L1 SlidingWindow 滑动窗口保存近期对话，L2 WorkingMemory 按重要性存储关键信息，L3 PersistentStore 持久化长期记忆"),
        Document(id="d2", content="Loom ContextOrchestrator 使用 EMA 自适应算法动态分配 token 预算，高相关源获得更多预算"),
    ])

    context = ContextOrchestrator()
    context.register(KnowledgeProvider(kb))

    agent2 = Agent(
        provider=provider,
        config=AgentConfig(max_steps=2),
        context=context,
    )
    r2 = await agent2.run(question)
    print(f"  回复: {r2.content[:200]}")


if __name__ == "__main__":
    asyncio.run(main())
