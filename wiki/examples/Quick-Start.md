# 快速开始示例

## 安装

```bash
pip install loom-agent
```

## 创建第一个 Agent

### 1. 配置 LLM

```python
from loom.providers.llm import OpenAIProvider

llm = OpenAIProvider(
    api_key="your-api-key",
    model="gpt-4",
    temperature=0.7
)
```

### 2. 创建 Agent

```python
from loom.agent import Agent

agent = Agent.create(
    llm,
    node_id="assistant",
    system_prompt="你是一个专业、友好的 AI 助手。",
)
```

### 3. 执行任务

```python
from loom.runtime import Task

task = Task(
    task_id="task-1",
    action="chat",
    parameters={"content": "你好！"}
)

result = await agent.execute_task(task)
print(result.result)
```

## 流式输出

```python
async for chunk in agent.stream_thinking():
    if chunk.type == "text":
        print(chunk.content, end="", flush=True)
```

## 添加工具

```python
from loom.tools import tool

@tool(name="calculator", description="数学计算")
async def calculator(expression: str) -> float:
    return eval(expression)

agent.add_tool(calculator)
```

## 完整示例

```python
import asyncio
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider
from loom.runtime import Task

async def main():
    # 配置 LLM
    llm = OpenAIProvider(api_key="your-api-key")

    # 创建 Agent
    agent = Agent.create(
        llm,
        node_id="assistant",
        system_prompt="你是一个专业、友好的 AI 助手。",
    )

    # 执行任务
    task = Task(
        task_id="task-1",
        action="chat",
        parameters={"content": "你好！"}
    )
    result = await agent.execute_task(task)
    print(result.result)

if __name__ == "__main__":
    asyncio.run(main())
```

## 下一步

- [创建研究小组](Research-Team)
- [工具开发](Tool-Development)

## 代码位置

- `examples/quick_start.py`

## 反向链接

被引用于: [Home](Home)
