# Loom API - FastAPI 风格的 Agent 创建接口

Loom 框架提供 FastAPI 风格的 API，具有类型安全、自动验证和直观设计。

## 设计理念

基于 **FastAPI 设计原则**：

1. **类型注解优先** - 使用 Python 类型注解
2. **Pydantic 验证** - 自动验证和序列化
3. **直观 API** - 简洁易用的接口
4. **依赖注入** - 自动管理依赖
5. **文档友好** - 自动生成文档（Pydantic schema）

## 核心组件

### LoomApp - 应用主类

管理 Agent、事件总线和调度器的主类。

```python
from loom.api import LoomApp

# 创建应用
app = LoomApp()
```

### AgentConfig - Pydantic 配置模型

类型安全的 Agent 配置模型，自动验证参数。

```python
from loom.api import AgentConfig

config = AgentConfig(
    agent_id="assistant",
    name="My Assistant",
    system_prompt="You are a helpful assistant",
    capabilities=["tool_use", "reflection"],
    max_iterations=10,
)
```

## 快速开始

### 基础使用

```python
from loom.api import LoomApp, AgentConfig
from loom.providers.llm import OpenAIProvider

# 1. 创建应用
app = LoomApp()

# 2. 配置 LLM Provider
llm = OpenAIProvider(api_key="your-api-key")
app.set_llm_provider(llm)

# 3. 创建 Agent
config = AgentConfig(
    agent_id="assistant",
    name="AI Assistant",
    system_prompt="You are a helpful AI assistant",
)

agent = app.create_agent(config)
print(f"Agent created: {agent.node_id}")
```

### 创建多个 Agent

```python
from loom.api import LoomApp, AgentConfig

app = LoomApp()
app.set_llm_provider(llm)

# 创建多个 Agent（共享事件总线和调度器）
agent1 = app.create_agent(AgentConfig(
    agent_id="chatbot",
    name="Chatbot",
    system_prompt="You are a friendly chatbot",
))

agent2 = app.create_agent(AgentConfig(
    agent_id="analyst",
    name="Data Analyst",
    system_prompt="You are a data analysis expert",
))

# 列出所有 Agent
print(f"Created {len(app.list_agents())} agents")
```

### 添加工具

```python
from loom.api import LoomApp, AgentConfig

def get_weather(city: str) -> str:
    """Get weather information."""
    return f"Weather in {city}: Sunny, 22°C"

# 全局工具（所有 Agent 可用）
app = LoomApp()
app.set_llm_provider(llm)
app.add_tools([get_weather])

# Agent 特定工具
def calculate(expr: str) -> float:
    """Calculate expression."""
    return eval(expr)

config = AgentConfig(
    agent_id="assistant",
    name="Assistant",
)

agent = app.create_agent(config, tools=[calculate])
```

### 链式调用

```python
from loom.api import LoomApp, AgentConfig
from loom.providers.llm import OpenAIProvider

# 支持方法链
app = (
    LoomApp()
    .set_llm_provider(OpenAIProvider(api_key="key"))
    .add_tools([get_weather, calculate])
)

agent = app.create_agent(AgentConfig(
    agent_id="agent",
    name="Agent",
))
```

## AgentConfig 参数

### 必需参数

- **`agent_id`** (str): Agent 唯一标识
  - 长度: 1-100 字符

- **`name`** (str): Agent 名称
  - 长度: 1-200 字符

### 可选参数

- **`system_prompt`** (str): 系统提示词
  - 默认: "You are a helpful AI assistant"

- **`capabilities`** (list[str]): Agent 能力列表
  - 有效值: "tool_use", "reflection", "planning", "multi_agent"
  - 默认: ["tool_use"]

- **`max_iterations`** (int): 最大迭代次数
  - 范围: 1-100
  - 默认: 10

- **`max_context_tokens`** (int): 最大上下文 token 数
  - 范围: 1000-1000000
  - 默认: 100000

- **`enable_observation`** (bool): 启用观测模式
  - 默认: True

- **`require_done_tool`** (bool): 需要 done 工具调用
  - 默认: True

## LoomApp 方法

### `set_llm_provider(provider: LLMProvider) -> LoomApp`

设置全局 LLM 提供者。

**参数:**
- `provider`: LLM 提供者实例

**返回:** Self（支持链式调用）

### `add_tools(tools: list) -> LoomApp`

添加全局工具。

**参数:**
- `tools`: 工具列表

**返回:** Self（支持链式调用）

### `create_agent(config: AgentConfig, ...) -> Agent`

创建 Agent。

**参数:**
- `config`: Agent 配置（Pydantic 模型）
- `llm_provider`: LLM 提供者（可选，默认使用全局）
- `tools`: Agent 特定工具（可选）
- `memory`: 自定义记忆系统（可选）

**返回:** Agent 实例

**异常:** ValueError（如果缺少 LLM provider）

### `get_agent(agent_id: str) -> Optional[Agent]`

获取已创建的 Agent。

**参数:**
- `agent_id`: Agent ID

**返回:** Agent 实例或 None

### `list_agents() -> list[str]`

列出所有 Agent ID。

**返回:** Agent ID 列表

## Pydantic 验证

AgentConfig 自动验证所有参数：

```python
from loom.api import AgentConfig
from pydantic import ValidationError

# 有效配置
config = AgentConfig(
    agent_id="agent-1",
    name="Agent 1",
    max_iterations=10,
)

# 无效配置（抛出 ValidationError）
try:
    config = AgentConfig(
        agent_id="agent-2",
        name="Agent 2",
        max_iterations=200,  # 超过最大值 100
    )
except ValidationError as e:
    print(f"验证错误: {e}")

# 无效能力（抛出 ValidationError）
try:
    config = AgentConfig(
        agent_id="agent-3",
        name="Agent 3",
        capabilities=["invalid_capability"],
    )
except ValidationError as e:
    print(f"验证错误: {e}")
```

## 完整示例

### 示例 1: 简单对话 Agent

```python
from loom.api import LoomApp, AgentConfig
from loom.providers.llm import OpenAIProvider

# 创建应用
app = LoomApp()

# 配置 LLM
llm = OpenAIProvider(
    api_key="sk-...",
    model="gpt-4"
)
app.set_llm_provider(llm)

# 创建 Agent
config = AgentConfig(
    agent_id="chat-agent",
    name="Chat Agent",
    system_prompt="You are a friendly chatbot",
)

agent = app.create_agent(config)
print(f"Created: {agent.node_id}")
```

### 示例 2: 多 Agent 协作系统

```python
from loom.api import LoomApp, AgentConfig
from loom.providers.llm import OpenAIProvider

# 创建应用
app = LoomApp()
app.set_llm_provider(OpenAIProvider(api_key="sk-..."))

# 创建多个专业 Agent
researcher = app.create_agent(AgentConfig(
    agent_id="researcher",
    name="Research Agent",
    system_prompt="You research topics thoroughly",
    capabilities=["tool_use", "planning"],
))

writer = app.create_agent(AgentConfig(
    agent_id="writer",
    name="Writer Agent",
    system_prompt="You write clear and engaging content",
    capabilities=["reflection", "tool_use"],
))

reviewer = app.create_agent(AgentConfig(
    agent_id="reviewer",
    name="Reviewer Agent",
    system_prompt="You review content for quality",
    capabilities=["reflection"],
))

print(f"Created {len(app.list_agents())} agents")
```

### 示例 3: 带工具的 Agent

```python
from loom.api import LoomApp, AgentConfig
from loom.providers.llm import OpenAIProvider

# 定义工具
def search_web(query: str) -> str:
    """Search the web."""
    return f"Search results for: {query}"

def calculate(expression: str) -> float:
    """Calculate mathematical expression."""
    return eval(expression)

# 创建应用并添加全局工具
app = LoomApp()
app.set_llm_provider(OpenAIProvider(api_key="sk-..."))
app.add_tools([search_web])

# 创建 Agent 并添加特定工具
config = AgentConfig(
    agent_id="assistant",
    name="Smart Assistant",
    system_prompt="You help with research and calculations",
    capabilities=["tool_use", "reflection"],
)

agent = app.create_agent(config, tools=[calculate])
print(f"Agent has access to global and specific tools")
```

## 核心 API 导出

### 协议层（A1）
- `NodeProtocol` - 节点协议
- `Task` - 任务模型
- `AgentCard` - 能力声明
- `AgentCapability` - 能力枚举

### 事件层（A2）
- `EventBus` - 事件总线
- `SSEFormatter` - SSE 格式化器

### 分形层（A3）
- `NodeContainer` - 节点容器

### 记忆层（A4）
- `LoomMemory` - 记忆系统
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

## 优势

### 1. 类型安全
完整的类型注解，IDE 支持更好：

```python
from loom.api import LoomApp, AgentConfig
from loom.orchestration import Agent

app: LoomApp = LoomApp()
config: AgentConfig = AgentConfig(agent_id="agent", name="Agent")
agent: Agent = app.create_agent(config)
```

### 2. 自动验证
Pydantic 自动验证参数，提供清晰的错误信息：

```python
# 自动验证范围
config = AgentConfig(
    agent_id="agent",
    name="Agent",
    max_iterations=200,  # ❌ ValidationError: max_iterations must be <= 100
)
```

### 3. 清晰错误
验证失败时提供明确的错误信息：

```python
try:
    config = AgentConfig(
        agent_id="agent",
        name="Agent",
        capabilities=["invalid"],
    )
except ValidationError as e:
    print(e)  # 显示具体的验证错误
```

### 4. 易于扩展
添加新字段只需修改 Pydantic 模型：

```python
class AgentConfig(BaseModel):
    # 添加新字段很简单
    new_field: str = "default"
```

## 参考文档

- [API Reference](../../docs/usage/api-reference.md) - 完整 API 参考
- [Getting Started](../../docs/usage/getting-started.md) - 快速开始指南
- [LLM Providers](../../docs/providers/llm-providers.md) - LLM 提供者文档
