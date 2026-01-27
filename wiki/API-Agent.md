# Agent API

## 创建 Agent

### 基础创建

```python
from loom.api import LoomApp, AgentConfig
from loom.providers.llm import OpenAIProvider

# 初始化应用
app = LoomApp()

# 配置 LLM
llm = OpenAIProvider(api_key="your-api-key")
app.set_llm_provider(llm)

# 创建 Agent
config = AgentConfig(
    agent_id="assistant",
    name="智能助手",
    system_prompt="你是一个专业、严谨的 AI 助手。",
    capabilities=["tool_use", "reflection"],
)

agent = app.create_agent(config)
```

### 高级配置

```python
config = AgentConfig(
    agent_id="researcher",
    name="研究员",
    system_prompt="你是专业的研究员...",
    capabilities=["tool_use", "reflection", "planning", "collaboration"],
    max_iterations=10,
    require_done_tool=True,
    enable_observation=True,
    max_context_tokens=4000,
)

agent = app.create_agent(config)
```

## 执行任务

### 同步执行

```python
from loom.protocol import Task

task = Task(
    task_id="task-1",
    action="explain",
    parameters={"content": "什么是递归？"}
)

result = await agent.execute_task(task)
print(result.result)
```

### 流式输出

```python
async for chunk in agent.stream_thinking():
    if chunk.type == "text":
        print(chunk.content, end="", flush=True)
```

### 事件订阅

```python
@agent.event_bus.subscribe("node.thinking")
async def on_thinking(event):
    print(f"Thinking: {event.data['content']}")

@agent.event_bus.subscribe("node.tool_call")
async def on_tool_call(event):
    print(f"Tool: {event.data['tool_name']}")
```

## 添加工具

### 定义工具

```python
from loom.tools import tool

@tool(
    name="calculator",
    description="执行数学计算"
)
async def calculator(expression: str) -> float:
    """计算数学表达式"""
    return eval(expression)
```

### 注册工具

```python
from loom.tools import ToolRegistry

registry = ToolRegistry()
registry.register_tool(calculator)

# 添加到 Agent
agent = Agent(
    node_id="assistant",
    llm_provider=llm,
    tool_registry=registry
)
```

## 分形组合

### 创建组合节点

```python
from loom.fractal import CompositeNode
from loom.fractal.strategies import ParallelStrategy

team = CompositeNode(
    node_id="research_team",
    children=[researcher, writer, editor],
    strategy=ParallelStrategy()
)

# 对外表现为单个 Agent
result = await team.execute_task(task)
```

## 参见

- 📖 [Agent 实现](design/Agent-Implementation)
- 💡 [示例代码](examples/Quick-Start)

## 代码位置

- `loom/api/`
- `loom/orchestration/agent.py`

## 反向链接

被引用于: [Home](Home)
