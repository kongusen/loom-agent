# Loom API - 框架顶层入口

`loom.api` 提供协议、事件、分形、记忆、编排与运行时的统一重导出。创建 Agent 请使用 `loom.agent` 的 **Agent.create()** 或 **Agent.builder()**。

## 设计理念

- **公理分层**：按 A1–A6 公理组织导出（协议 / 事件 / 分形 / 记忆 / 编排 / 运行时）
- **类型安全**：完整类型注解，IDE 友好
- **事件驱动**：通信基于 CloudEvents，可观测

## 创建 Agent（推荐）

Agent 不再通过 `loom.api` 创建，请直接使用 **loom.agent**：

### 一步创建：Agent.create()

```python
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider

llm = OpenAIProvider(api_key="your-api-key")

agent = Agent.create(
    llm,
    node_id="assistant",
    system_prompt="You are a helpful AI assistant",
)
print(f"Agent created: {agent.node_id}")
```

### 链式配置：Agent.builder()

```python
from loom.agent import Agent

agent = (
    Agent.builder(llm)
    .with_system_prompt("You are a helpful AI assistant")
    .with_tools([...])
    .with_memory(max_tokens=4000)
    .build()
)
```

### 创建多个 Agent

```python
from loom.agent import Agent

agent1 = Agent.create(
    llm,
    node_id="chatbot",
    system_prompt="You are a friendly chatbot",
)

agent2 = Agent.create(
    llm,
    node_id="analyst",
    system_prompt="You are a data analysis expert",
)
```

### 带工具的 Agent

```python
from loom.agent import Agent
from loom.tools.registry import ToolRegistry

def get_weather(city: str) -> str:
    """Get weather information."""
    return f"Weather in {city}: Sunny, 22°C"

tool_registry = ToolRegistry()
tool_registry.register_function(get_weather)

tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get weather for a city",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"]
        }
    }
}]

agent = Agent.create(
    llm,
    node_id="weather-assistant",
    system_prompt="You help with weather queries",
    tools=tools,
    tool_registry=tool_registry,
)
```

## loom.api 导出内容

本包**不再**导出 LoomApp 或 AgentConfig（已在 v0.5.0 移除）。当前导出按公理分层：

### 协议层（A1）
- `NodeProtocol` - 节点协议
- `Task` - 任务模型
- `TaskStatus` - 任务状态
- `AgentCard` - 能力声明
- `AgentCapability` - 能力枚举

### 事件层（A2）
- `EventBus` - 事件总线
- `SSEFormatter` - SSE 格式化器

### 分形层（A3）
- `NodeContainer` - 节点容器

### 记忆层（A4）
- `MemoryManager` - 记忆管理
- `MemoryUnit` - 记忆单元
- `MemoryTier` - 记忆层级
- `MemoryType` - 记忆类型
- `MemoryQuery` - 记忆查询

### 编排层（A5）
- `RouterOrchestrator` - 路由编排
- `CrewOrchestrator` - 团队编排

### 运行时
- `Dispatcher` - 调度器
- `Interceptor` - 拦截器
- `InterceptorChain` - 拦截器链

### 流式观测
- 使用 `from loom.api.stream_api import StreamAPI` 获取流式观测能力。

## 参考文档

- [API Reference](../../docs/usage/api-reference.md) - 完整 API 参考
- [Getting Started](../../docs/usage/getting-started.md) - 快速开始
- [Agent 创建方式](../../docs/usage/api-reference.md#basic-creation-with-agentcreate) - Agent.create() 参数说明
