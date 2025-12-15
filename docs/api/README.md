# API 参考

**版本**: v0.1.9
**最后更新**: 2024-12-15

Loom Agent 完整 API 参考文档。

---

## 📚 API 文档

### [Agents API](./agents.md)
Agent 相关 API

- **SimpleAgent**: 核心 Agent 实现
- **BaseAgent**: Agent 协议定义
- Skills 管理方法
- 统计和监控

### [Patterns API](./patterns.md)
多 Agent 协作模式 API

- **Crew**: 多 Agent 协作
- **CrewRole**: 角色定义
- 智能协调（SmartCoordinator）
- 并行执行（ParallelExecutor）
- 容错恢复（ErrorRecovery）
- 可观测性（Tracer, Evaluator）
- 预设配置（CrewPresets）

### [Core API](./core.md)
核心组件 API

- **Message**: 统一消息格式
- **BaseAgent**: Agent 协议
- **AgentExecutor**: 执行引擎
- **ContextManager**: 上下文管理
- 事件系统（Events）
- 错误处理（Errors）

### [Tools API](./tools.md)
工具创建和管理 API

- **@tool**: 工具装饰器
- **ToolBuilder**: 工具构建器
- **BaseTool**: 工具协议
- 工具注册和组合

---

## 🚀 快速开始

### 基础示例

```python
import asyncio
import loom, Message
from loom.builtin import OpenAILLM, tool

@tool(name="calculator")
async def calculator(expression: str) -> float:
    """计算数学表达式"""
    return eval(expression)

async def main():
    agent = loom.agent(
        name="assistant",
        llm=OpenAILLM(api_key="..."),
        tools=[calculator]
    )

    msg = Message(role="user", content="计算 123 * 456")
    response = await agent.run(msg)
    print(response.content)

asyncio.run(main())
```

---

## 📖 按功能查找

### Agent 相关

| 功能 | API | 文档 |
|------|-----|------|
| 创建 Agent | `loom.agent()` | [Agents API](./agents.md#simpleagent) |
| 执行任务 | `agent.run()` | [Agents API](./agents.md#run) |
| 管理 Skills | `agent.list_skills()` | [Agents API](./agents.md#skills-管理方法) |
| 获取统计 | `agent.get_stats()` | [Agents API](./agents.md#get_stats) |

### 多 Agent 协作

| 功能 | API | 文档 |
|------|-----|------|
| 创建 Crew | `Crew()` | [Patterns API](./patterns.md#crew) |
| 顺序执行 | `sequential_crew()` | [Patterns API](./patterns.md#sequential_crew) |
| 并行执行 | `parallel_crew()` | [Patterns API](./patterns.md#parallel_crew) |
| 智能协调 | `coordinated_crew()` | [Patterns API](./patterns.md#coordinated_crew) |
| 预设配置 | `CrewPresets.*` | [Patterns API](./patterns.md#预设配置) |

### 消息和上下文

| 功能 | API | 文档 |
|------|-----|------|
| 创建消息 | `Message()` | [Core API](./core.md#message) |
| 上下文管理 | `ContextManager()` | [Core API](./core.md#contextmanager) |
| 事件监听 | `event_handler` | [Core API](./core.md#events) |

### 工具开发

| 功能 | API | 文档 |
|------|-----|------|
| 创建工具 | `@tool` | [Tools API](./tools.md#tool-装饰器) |
| 构建工具 | `ToolBuilder()` | [Tools API](./tools.md#toolbuilder) |
| 自定义工具 | `BaseTool` | [Tools API](./tools.md#basetool) |

---

## 🔍 按用例查找

### 基础使用

```python
# 简单对话
agent = loom.agent(name="assistant", llm=llm)
response = await agent.run(Message(role="user", content="Hello"))
```

→ [Agents API](./agents.md)

### 带工具的 Agent

```python
@tool()
async def search(query: str) -> str:
    return f"Results for {query}"

agent = loom.agent(name="agent", llm=llm, tools=[search])
```

→ [Tools API](./tools.md)

### 多 Agent 协作

```python
crew = Crew(agents=[agent1, agent2], mode="sequential")
result = await crew.run("任务描述")
```

→ [Patterns API](./patterns.md)

### 事件监控

```python
def event_handler(event):
    print(f"Event: {event.type}")

agent = loom.agent(name="agent", llm=llm, event_handler=event_handler)
```

→ [Core API - Events](./core.md#events)

### Skills 系统

```python
agent = loom.agent(
    name="agent",
    llm=llm,
    enable_skills=True,
    skills_dir="./skills"
)

skills = agent.list_skills()
```

→ [Agents API - Skills](./agents.md#skills-管理方法)

---

## 📦 内置实现

### LLM

```python
from loom.builtin import OpenAILLM

llm = OpenAILLM(
    api_key="...",
    model="gpt-4",
    temperature=0.7
)
```

### Memory

```python
from loom.builtin import InMemoryMemory, PersistentMemory

# 内存 Memory
memory = InMemoryMemory()

# 持久化 Memory
memory = PersistentMemory(path="./memory.json")
```

### Compression

```python
from loom.builtin import StructuredCompressor, CompressionConfig

compressor = StructuredCompressor(
    llm=llm,
    config=CompressionConfig(
        max_tokens=2000,
        strategy="structured"
    )
)
```

---

## 🎯 常见模式

### 模式 1：单 Agent + 工具

```python
import loom
from loom.builtin import OpenAILLM, tool

@tool()
async def tool1(...): pass

@tool()
async def tool2(...): pass

agent = loom.agent(
    name="agent",
    llm=OpenAILLM(api_key="..."),
    tools=[tool1, tool2]
)
```

### 模式 2：多 Agent 协作

```python
from loom.patterns import Crew

agent1 = loom.agent(name="agent1", llm=llm)
agent2 = loom.agent(name="agent2", llm=llm)

crew = Crew(agents=[agent1, agent2], mode="sequential")
```

### 模式 3：事件驱动

```python
def event_handler(event):
    if event.type == AgentEventType.LLM_END:
        print(f"Tokens: {event.data['tokens_input']}")

agent = loom.agent(
    name="agent",
    llm=llm,
    event_handler=event_handler
)
```

### 模式 4：Skills 增强

```python
agent = loom.agent(
    name="agent",
    llm=llm,
    enable_skills=True
)

# Skills 自动加载
skills = agent.list_skills()
```

---

## 🔗 相关资源

### 入门指南
- [5分钟快速开始](../getting-started/quickstart.md)
- [创建第一个 Agent](../getting-started/first-agent.md)
- [API 快速参考](../getting-started/quick-reference.md)

### 使用指南
- [SimpleAgent 指南](../guides/agents/simple-agent.md)
- [Crew 协作指南](../guides/patterns/crew.md)
- [工具开发指南](../guides/tools/development.md)
- [Skills 系统](../guides/skills/overview.md)

### 架构文档
- [架构概述](../architecture/overview.md)
- [故障排除](../architecture/troubleshooting.md)

---

## 📝 API 版本

当前版本：**v0.1.9**

### v0.1.9 核心改进

**Core**:
- `Message` 架构修复（history 正式化，零数据丢失）
- `get_message_history()` 安全提取函数
- `build_history_chain()` 不可变历史链构建
- `serialize_tool_result()` 工具结果结构化序列化

**Memory**:
- `HierarchicalMemory` 优化（智能晋升、异步向量化、调试模式）
- 智能记忆晋升（过滤 trivial 内容，LLM 摘要）
- 异步向量化（10x 吞吐量提升）
- Ephemeral Memory 调试模式

**完整架构**:
- Crew（4种协作模式）
- Router（智能路由）
- 递归控制模式（ReAct/反思/思维树）
- ContextAssembler（智能上下文组装）
- Skills 系统（渐进式披露）

---

## 💡 提示

### 类型提示

所有 API 都有完整的类型注解，支持 IDE 自动补全：

```python
import loom, Message
from loom.builtin import OpenAILLM

agent: SimpleAgent = loom.agent(...)
message: Message = Message(...)
```

### 异步编程

大部分 API 都是异步的，需要使用 `async/await`：

```python
import asyncio

async def main():
    response = await agent.run(message)

asyncio.run(main())
```

### 错误处理

使用框架提供的错误类：

```python
from loom.core.errors import AgentError, ToolError, LLMError

try:
    response = await agent.run(message)
except ToolError:
    print("工具调用失败")
except LLMError:
    print("LLM 调用失败")
except AgentError:
    print("Agent 执行失败")
```

---

**返回**: [文档首页](../README.md)
