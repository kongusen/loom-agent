# Core API

**版本**: v0.1.6

Core API 参考文档 - 核心组件。

---

## 📋 目录

1. [Message](#message)
2. [BaseAgent](#baseagent)
3. [AgentExecutor](#agentexecutor)
4. [ContextManager](#contextmanager)
5. [Events](#events)
6. [Errors](#errors)

---

## Message

### 概述

`Message` 是统一的消息格式，携带所有状态信息。

```python
from loom import Message

msg = Message(role="user", content="Hello")
```

### 数据类定义

```python
@dataclass
class Message:
    role: str                                    # "user" | "assistant" | "system"
    content: str                                 # 消息内容
    tool_calls: Optional[List[ToolCall]] = None  # 工具调用
    tool_results: Optional[List[ToolResult]] = None  # 工具结果
    metadata: Optional[Dict[str, Any]] = None    # 元数据
```

#### 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `role` | `str` | 角色：user / assistant / system |
| `content` | `str` | 消息内容 |
| `tool_calls` | `List[ToolCall]` | 工具调用列表 |
| `tool_results` | `List[ToolResult]` | 工具结果列表 |
| `metadata` | `Dict` | 元数据（自定义） |

#### 示例

**用户消息**：
```python
msg = Message(role="user", content="计算 2+2")
```

**带工具调用的消息**：
```python
msg = Message(
    role="assistant",
    content="",
    tool_calls=[
        ToolCall(
            id="call_123",
            name="calculator",
            arguments={"expression": "2+2"}
        )
    ]
)
```

**带工具结果的消息**：
```python
msg = Message(
    role="user",
    content="",
    tool_results=[
        ToolResult(
            id="call_123",
            name="calculator",
            result="4"
        )
    ]
)
```

**带元数据**：
```python
msg = Message(
    role="user",
    content="Hello",
    metadata={
        "user_id": "user_123",
        "session_id": "session_456",
        "timestamp": 1234567890
    }
)
```

---

### 方法

#### `to_dict()`

转换为字典。

```python
def to_dict(self) -> dict
```

**返回值**：
```python
{
    "role": str,
    "content": str,
    "tool_calls": [...],  # 如果有
    "tool_results": [...],  # 如果有
    "metadata": {...}  # 如果有
}
```

#### `from_dict()`

从字典创建。

```python
@classmethod
def from_dict(cls, data: dict) -> Message
```

**示例**：
```python
data = {
    "role": "user",
    "content": "Hello"
}
msg = Message.from_dict(data)
```

---

## BaseAgent

### 概述

`BaseAgent` 是 Agent 的协议定义。

```python
from loom.core import BaseAgent
```

### 协议

```python
class BaseAgent(Protocol):
    name: str
    llm: BaseLLM
    tools: List[BaseTool]

    async def run(self, message: Message) -> Message:
        ...
```

### 工具函数

#### `create_agent()`

创建 Agent 实例。

```python
from loom import create_agent

agent = create_agent(
    agent_type="simple",
    name="assistant",
    llm=llm
)
```

#### `is_agent()`

检查是否是 Agent。

```python
from loom.core import is_agent

if is_agent(obj):
    print("This is an agent")
```

#### `validate_agent()`

验证 Agent 是否符合协议。

```python
from loom.core import validate_agent

try:
    validate_agent(my_agent)
    print("Valid agent")
except ValidationError as e:
    print(f"Invalid: {e}")
```

---

## AgentExecutor

### 概述

`AgentExecutor` 是 Agent 的执行引擎，实现递归逻辑。

```python
from loom.core import AgentExecutor

executor = AgentExecutor(
    agent_name="assistant",
    llm=llm,
    tools=[],
    system_prompt="...",
    context_manager=context_mgr,
    max_recursion_depth=20
)
```

### 构造函数

```python
AgentExecutor(
    agent_name: str,
    llm: BaseLLM,
    tools: List[BaseTool] = None,
    system_prompt: Optional[str] = None,
    context_manager: Optional[ContextManager] = None,
    max_recursion_depth: int = 20,
    event_handler: Optional[Callable] = None
)
```

#### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `agent_name` | `str` | 必需 | Agent 名称 |
| `llm` | `BaseLLM` | 必需 | LLM 实例 |
| `tools` | `List[BaseTool]` | `[]` | 工具列表 |
| `system_prompt` | `str` | `None` | 系统提示 |
| `context_manager` | `ContextManager` | `None` | 上下文管理器 |
| `max_recursion_depth` | `int` | `20` | 最大递归深度 |
| `event_handler` | `Callable` | `None` | 事件处理函数 |

---

### 核心方法

#### `execute()`

执行消息（递归）。

```python
async def execute(self, message: Message) -> Message
```

**执行流程**：
1. 发出 `agent_start` 事件
2. 组装上下文（历史消息 + 系统提示）
3. 调用 LLM
4. 如果有 tool_calls：
   - 并行执行所有工具
   - 递归调用 `execute()`
5. 返回最终 Message

**示例**：
```python
msg = Message(role="user", content="计算 2+2")
response = await executor.execute(msg)
print(response.content)
```

---

#### `reset()`

重置执行器状态。

```python
def reset(self) -> None
```

**用途**：
- 清除对话历史
- 重置统计信息

---

#### `get_stats()`

获取统计信息。

```python
def get_stats(self) -> dict
```

**返回值**：
```python
{
    "total_llm_calls": int,         # LLM 调用次数
    "total_tool_calls": int,        # 工具调用次数
    "total_tokens_input": int,      # 输入 token 数
    "total_tokens_output": int,     # 输出 token 数
    "total_cost": float,            # 总成本
    "llm_breakdown": {              # LLM 调用详情
        "model_name": str,
        "calls": int,
        "tokens": int,
        "cost": float
    },
    "tool_breakdown": [             # 工具调用详情
        {
            "name": str,
            "calls": int,
            "avg_duration": float
        }
    ]
}
```

---

## ContextManager

### 概述

`ContextManager` 管理对话历史和上下文。

```python
from loom.core import ContextManager

context_mgr = ContextManager(
    max_history=100,
    compressor=compressor
)
```

### 构造函数

```python
ContextManager(
    max_history: int = 100,
    compressor: Optional[BaseCompressor] = None,
    memory: Optional[BaseMemory] = None
)
```

#### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_history` | `int` | `100` | 最大历史消息数 |
| `compressor` | `BaseCompressor` | `None` | 压缩器 |
| `memory` | `BaseMemory` | `None` | Memory 实例 |

---

### 核心方法

#### `add_message()`

添加消息到历史。

```python
def add_message(self, message: Message) -> None
```

**示例**：
```python
context_mgr.add_message(Message(role="user", content="Hello"))
```

---

#### `get_messages()`

获取历史消息。

```python
def get_messages(
    self,
    limit: Optional[int] = None,
    include_system: bool = True
) -> List[Message]
```

**参数**：
- `limit` (`int`, 可选): 限制数量
- `include_system` (`bool`): 是否包含系统消息

**返回值**：
- `List[Message]`: 消息列表

---

#### `assemble_context()`

组装完整上下文（系统提示 + 历史）。

```python
def assemble_context(
    self,
    system_prompt: Optional[str] = None
) -> List[Message]
```

**返回值**：
- `List[Message]`: 完整上下文

---

#### `clear()`

清除历史。

```python
def clear(self) -> None
```

---

#### `compress()`

压缩历史（如果配置了压缩器）。

```python
async def compress(self) -> None
```

**自动触发**：当历史消息超过 `max_history` 时

---

### 工厂函数

#### `create_context_manager()`

创建 ContextManager。

```python
from loom import create_context_manager

context_mgr = create_context_manager(
    max_history=100,
    enable_compression=True,
    enable_memory=True
)
```

---

## Events

### AgentEvent

事件数据类。

```python
@dataclass
class AgentEvent:
    type: AgentEventType
    agent_name: str
    timestamp: float
    data: Dict[str, Any]
```

---

### AgentEventType

事件类型枚举。

```python
class AgentEventType(Enum):
    # Agent 事件
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    AGENT_ERROR = "agent_error"

    # LLM 事件
    LLM_START = "llm_start"
    LLM_END = "llm_end"
    LLM_ERROR = "llm_error"

    # Tool 事件
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOOL_ERROR = "tool_error"

    # Context 事件
    CONTEXT_UPDATE = "context_update"
    CONTEXT_COMPRESS = "context_compress"
```

---

### 使用事件

```python
from loom.core.events import AgentEventType

def event_handler(event: AgentEvent):
    if event.type == AgentEventType.AGENT_START:
        print(f"🚀 Agent {event.agent_name} started")

    elif event.type == AgentEventType.LLM_START:
        print(f"🤖 LLM call started")

    elif event.type == AgentEventType.LLM_END:
        data = event.data
        print(f"✅ LLM call completed:")
        print(f"   Tokens: {data['tokens_input']} + {data['tokens_output']}")
        print(f"   Cost: ${data['cost']:.4f}")

    elif event.type == AgentEventType.TOOL_START:
        print(f"🔧 Tool call: {event.data['tool_name']}")

    elif event.type == AgentEventType.TOOL_END:
        duration = event.data['duration']
        print(f"✅ Tool completed in {duration:.2f}s")

agent = loom.agent(
    name="assistant",
    llm=llm,
    event_handler=event_handler
)
```

---

## Errors

### 错误层次结构

```
LoomError (基类)
├── AgentError
│   ├── ExecutionError
│   └── RecursionError
├── ToolError
├── ContextError
│   ├── CompressionError
│   └── MemoryError
├── LLMError
├── ValidationError
└── ConfigurationError
```

---

### LoomError

基础错误类。

```python
class LoomError(Exception):
    """Loom 框架基础错误"""
    pass
```

---

### AgentError

Agent 相关错误。

```python
class AgentError(LoomError):
    """Agent 错误"""
    pass
```

**子类**：
- `ExecutionError`: 执行错误
- `RecursionError`: 递归深度超限

---

### ToolError

工具调用错误。

```python
class ToolError(LoomError):
    """工具错误"""
    pass
```

---

### ContextError

上下文管理错误。

```python
class ContextError(LoomError):
    """上下文错误"""
    pass
```

**子类**：
- `CompressionError`: 压缩错误
- `MemoryError`: Memory 错误

---

### LLMError

LLM 调用错误。

```python
class LLMError(LoomError):
    """LLM 错误"""
    pass
```

---

### 错误处理示例

```python
import loom, Message
from loom.core.errors import (
    AgentError, ExecutionError, ToolError, LLMError
)

agent = loom.agent(name="assistant", llm=llm)

try:
    msg = Message(role="user", content="...")
    response = await agent.run(msg)

except RecursionError:
    print("递归深度超限")

except ToolError as e:
    print(f"工具调用失败: {e}")

except LLMError as e:
    print(f"LLM 调用失败: {e}")

except ExecutionError as e:
    print(f"执行错误: {e}")

except AgentError as e:
    print(f"Agent 错误: {e}")

except LoomError as e:
    print(f"框架错误: {e}")
```

---

## 完整示例

### 基础使用

```python
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM

# 创建 Agent
agent = loom.agent(
    name="assistant",
    llm=OpenAILLM(api_key="...")
)

# 创建消息
msg = Message(role="user", content="Hello")

# 执行
response = await agent.run(msg)
print(response.content)

# 统计
stats = agent.get_stats()
print(f"LLM calls: {stats['executor_stats']['total_llm_calls']}")
```

### 高级使用

```python
from loom.core import (
    AgentExecutor, ContextManager, AgentEventType
)
from loom.builtin import (
    OpenAILLM, StructuredCompressor, InMemoryMemory
)

# 创建组件
llm = OpenAILLM(api_key="...")
compressor = StructuredCompressor(llm=llm)
memory = InMemoryMemory()

context_mgr = ContextManager(
    max_history=50,
    compressor=compressor,
    memory=memory
)

def event_handler(event):
    print(f"[{event.type.value}] {event.agent_name}")

executor = AgentExecutor(
    agent_name="advanced-agent",
    llm=llm,
    tools=[],
    context_manager=context_mgr,
    max_recursion_depth=15,
    event_handler=event_handler
)

# 执行
msg = Message(role="user", content="...")
response = await executor.execute(msg)

# 查看历史
history = context_mgr.get_messages()
print(f"历史消息数: {len(history)}")

# 统计
stats = executor.get_stats()
print(f"Token 数: {stats['total_tokens_input'] + stats['total_tokens_output']}")
```

---

## 相关文档

- [架构设计](../architecture/overview.md) - 框架架构
- [Agents API](./agents.md) - Agent API 参考
- [快速开始](../getting-started/quickstart.md) - 快速入门

---

**返回**: [API 参考](./README.md) | [文档首页](../README.md)
