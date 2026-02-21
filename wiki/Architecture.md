# Architecture

Loom 采用组合架构，从单 Agent 到多 Agent 委派，再到全栈流水线逐层构建。

## 多 Agent 委派

父子 Agent 通过 EventBus 传播事件，协调者按领域路由任务：

```python
from loom import Agent, AgentConfig, EventBus

bus = EventBus(node_id="root")

# 子 Agent
researcher = Agent(
    provider=provider, name="researcher",
    config=AgentConfig(system_prompt="你是研究员", max_steps=2),
    event_bus=bus.create_child("researcher"),
)
writer = Agent(
    provider=provider, name="writer",
    config=AgentConfig(system_prompt="你是写作者", max_steps=2),
    event_bus=bus.create_child("writer"),
)

# 委派执行
r1 = await researcher.run("研究 AI Agent 记忆系统")
r2 = await writer.run("撰写技术文章")

# 事件冒泡 — 所有子 Agent 事件汇聚到根节点
events_log = []
async def log_event(e): events_log.append(e.type)
bus.on_all(log_event)
```

## 全栈流水线

将所有模块组合到单个 Agent，展示完整架构：

```python
from loom import (
    Agent, AgentConfig, EventBus, InterceptorChain, InterceptorContext,
    MemoryManager, SlidingWindow, WorkingMemory,
    ContextOrchestrator, KnowledgeBase, KnowledgeProvider,
    ToolRegistry, define_tool, Document,
)

# 1. 事件总线
bus = EventBus(node_id="main")

# 2. 记忆
memory = MemoryManager(
    l1=SlidingWindow(token_budget=100),
    l2=WorkingMemory(token_budget=200),
)

# 3. 知识库 + Context
kb = KnowledgeBase(embedder=embedder, vector_store=vector_store)
await kb.ingest([Document(id="d1", content="...")])
context = ContextOrchestrator()
context.register(KnowledgeProvider(kb))

# 4. 工具
tools = ToolRegistry()
tools.register(define_tool("search", "搜索", SearchParams, search_fn))

# 5. 拦截器
interceptors = InterceptorChain()
interceptors.use(AuditInterceptor())

# 6. 组装
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

result = await agent.run("什么是 AI Agent?")
```

## 架构层次图

```
┌─────────────────────────────────────────┐
│              Runtime / AmoebaLoop        │
│  ┌───────────────────────────────────┐  │
│  │         ClusterManager            │  │
│  │   RewardBus · LifecycleManager    │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │            Agent                  │  │
│  │  ┌─────────┐  ┌───────────────┐  │  │
│  │  │ Memory  │  │ Interceptors  │  │  │
│  │  │ L1/L2/L3│  │   Chain       │  │  │
│  │  └─────────┘  └───────────────┘  │  │
│  │  ┌─────────┐  ┌───────────────┐  │  │
│  │  │ Tools   │  │ Context       │  │  │
│  │  │Registry │  │ Orchestrator  │  │  │
│  │  └─────────┘  └───────────────┘  │  │
│  │  ┌─────────┐  ┌───────────────┐  │  │
│  │  │EventBus │  │ Skills        │  │  │
│  │  │Parent→  │  │ Registry      │  │  │
│  │  └─────────┘  └───────────────┘  │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │     BaseLLMProvider               │  │
│  │     Retry + CircuitBreaker        │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │     KnowledgeBase (RAG)           │  │
│  │     Chunker → Embedder → Vector   │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## 错误体系

```python
from loom import (
    LoomError,                # 基类
    LLMError,                 # LLM 调用错误
    LLMRateLimitError,        # 速率限制
    LLMAuthError,             # 认证失败
    ToolError,                # 工具执行错误
    ToolTimeoutError,         # 工具超时
    AgentMaxStepsError,       # 超过最大步数
    AuctionNoWinnerError,     # 拍卖无胜出者
)
```

## 模块导航

| 模块 | 文档 | Demo |
|------|------|------|
| Agent 核心 | [Agent](Agent) | 01 |
| 工具系统 | [Tools](Tools) | 02 |
| 事件总线 | [Events](Events) | 03 |
| 拦截器 | [Interceptors](Interceptors) | 04 |
| 记忆层级 | [Memory](Memory) | 05 |
| 知识库 RAG | [Knowledge](Knowledge) | 06 |
| 上下文编排 | [Context](Context) | 07 |
| 技能系统 | [Skills](Skills) | 08 |
| 集群拍卖 | [Cluster](Cluster) | 09-10 |
| 弹性 Provider | [Providers](Providers) | 11 |
| 运行时 | [Runtime](Runtime) | 12-13 |

> 完整示例：[`examples/demo/14_delegation.py`](../examples/demo/14_delegation.py) | [`examples/demo/15_full_stack.py`](../examples/demo/15_full_stack.py)
