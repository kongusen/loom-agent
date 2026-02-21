"""15 — 全栈流水线：Agent + Memory + Knowledge + Context + Events + Interceptors + Tools。"""

import asyncio

from _provider import OpenAIEmbedder, create_provider
from pydantic import BaseModel

from loom import (
    Agent,
    AgentConfig,
    ContextOrchestrator,
    Document,
    EventBus,
    InterceptorChain,
    InterceptorContext,
    KnowledgeBase,
    KnowledgeProvider,
    MemoryManager,
    SlidingWindow,
    ToolRegistry,
    WorkingMemory,
    define_tool,
)
from loom.knowledge import InMemoryVectorStore


# ── 工具 ──
class SearchParams(BaseModel):
    query: str


async def search_exec(params, ctx):
    return f"搜索结果: 找到关于 '{params.query}' 的 3 篇文档"


# ── 拦截器 ──
class AuditInterceptor:
    name = "audit"

    async def intercept(self, ctx: InterceptorContext, nxt):
        ctx.metadata["audited"] = True
        await nxt()


async def main():
    print("=" * 50)
    print("Loom v0.6.0 全栈流水线")
    print("=" * 50)

    # 1. 基础设施
    provider = create_provider()
    bus = EventBus(node_id="main")
    events = []

    async def log(e):
        events.append(e.type)

    bus.on_all(log)

    # 2. 记忆
    memory = MemoryManager(
        l1=SlidingWindow(token_budget=100),
        l2=WorkingMemory(token_budget=200),
    )

    # 3. 知识库
    kb = KnowledgeBase(embedder=OpenAIEmbedder(), vector_store=InMemoryVectorStore())
    await kb.ingest(
        [
            Document(id="d1", content="AI Agent 采用 ReAct 模式：推理+行动循环"),
            Document(id="d2", content="记忆系统分为 L1 工作记忆、L2 短期、L3 长期"),
        ]
    )

    # 4. Context + Knowledge Provider
    context = ContextOrchestrator()
    context.register(KnowledgeProvider(kb))

    # 5. 工具
    tools = ToolRegistry()
    tools.register(define_tool("search", "搜索知识库", SearchParams, search_exec))

    # 6. 拦截器
    interceptors = InterceptorChain()
    interceptors.use(AuditInterceptor())

    # 7. 组装 Agent
    agent = Agent(
        provider=provider,
        config=AgentConfig(system_prompt="你是 AI 专家", max_steps=3),
        name="full-stack",
        memory=memory,
        tools=tools,
        context=context,
        event_bus=bus,
        interceptors=interceptors,
    )

    # 8. 运行
    print("\n[运行] 查询: 什么是 AI Agent?")
    result = await agent.run("什么是 AI Agent?")
    print(f"  回复: {result.content}")
    print(f"  token: {result.usage.total_tokens}")

    # 9. 验证各层
    print("\n[验证]")
    print(f"  事件数: {len(events)}")
    print(f"  L1 消息: {len(memory.l1.get_messages())}")
    l2 = await memory.l2.retrieve()
    print(f"  L2 条目: {len(l2)}")
    print("  知识库文档: 2")
    print(f"  工具: {[t.name for t in tools.list()]}")
    print("  拦截器: 1 (audit)")

    print("\n" + "=" * 50)
    print("全栈流水线完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
