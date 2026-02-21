# Agent

Agent 是 Loom 的核心执行单元，采用组合模式将 provider、memory、tools、context 等模块注入，形成完整的 LLM 对话循环。

## API

```python
class Agent:
    def __init__(
        self,
        provider: LLMProvider,           # LLM 提供者（必需）
        config: AgentConfig = None,      # 配置
        name: str = None,                # 名称（默认自动生成）
        memory: MemoryManager = None,    # 记忆管理器
        tools: ToolRegistry = None,      # 工具注册表
        context: ContextOrchestrator = None,  # 上下文编排
        event_bus: EventBus = None,      # 事件总线
        interceptors: InterceptorChain = None,  # 拦截器链
        strategy: LoopStrategy = None,   # 循环策略
    )

    async def run(self, input_text: str) -> DoneEvent
    async def stream(self, input_text: str) -> AsyncGenerator[AgentEvent, None]
```

## AgentConfig

```python
@dataclass
class AgentConfig:
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: str | None = None
    base_url: str | None = None
    system_prompt: str = "You are a helpful assistant."
    max_steps: int = 10
    temperature: float = 0.7
    max_tokens: int = 4096
    token_budget: int = 128_000
    stream: bool = True
```

## 基础用法 — run()

一次性获取完整回复：

```python
from loom import Agent, AgentConfig
from loom.providers.openai import OpenAIProvider

provider = OpenAIProvider(AgentConfig(api_key="sk-xxx", model="gpt-4o-mini"))
agent = Agent(
    provider=provider,
    config=AgentConfig(system_prompt="你是助手", max_steps=3),
    name="demo-agent",
)

result = await agent.run("用一句话介绍 Python")
print(result.content)   # Python是一种简洁易读的高级编程语言...
print(result.usage.total_tokens)
```

## 流式输出 — stream()

逐 token 流式返回事件：

```python
from loom import TextDeltaEvent, DoneEvent

async for event in agent.stream("用一句话介绍 Rust"):
    if isinstance(event, TextDeltaEvent):
        print(event.text, end="", flush=True)
    elif isinstance(event, DoneEvent):
        print(f"\n完成, steps={event.steps}")
```

## 事件类型

| 事件 | 说明 |
|------|------|
| `TextDeltaEvent` | 文本增量（流式 token） |
| `StepStartEvent` | 步骤开始 |
| `StepEndEvent` | 步骤结束 |
| `ToolCallStartEvent` | 工具调用开始 |
| `ToolCallEndEvent` | 工具调用结束 |
| `ErrorEvent` | 错误 |
| `DoneEvent` | 完成（含 content, steps, usage） |

## 组合注入

Agent 的能力通过组合注入扩展，每个模块独立可选：

```python
agent = Agent(
    provider=provider,
    config=AgentConfig(system_prompt="你是 AI 专家", max_steps=3),
    memory=MemoryManager(l1=SlidingWindow(token_budget=2000)),
    tools=tool_registry,
    context=context_orchestrator,
    event_bus=EventBus(node_id="main"),
    interceptors=interceptor_chain,
)
```

详见各模块文档：[Tools](Tools) | [Memory](Memory) | [Events](Events) | [Interceptors](Interceptors) | [Context](Context)

> 完整示例：[`examples/demo/01_hello_agent.py`](../examples/demo/01_hello_agent.py)
