# 快速开始示例

## 安装

```bash
pip install loom-agent
```

## 创建第一个 Agent

### 1. 初始化应用

```python
from loom.api import LoomApp
from loom.providers.llm import OpenAIProvider

app = LoomApp()
```

### 2. 配置 LLM

```python
llm = OpenAIProvider(
    api_key="your-api-key",
    model="gpt-4",
    temperature=0.7
)

app.set_llm_provider(llm)
```

### 3. 创建 Agent

```python
from loom.api import AgentConfig

config = AgentConfig(
    agent_id="assistant",
    name="智能助手",
    system_prompt="你是一个专业、友好的 AI 助手。",
)

agent = app.create_agent(config)
```

### 4. 执行任务

```python
from loom.protocol import Task

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
from loom.api import LoomApp, AgentConfig
from loom.providers.llm import OpenAIProvider
from loom.protocol import Task

async def main():
    # 初始化
    app = LoomApp()
    llm = OpenAIProvider(api_key="your-api-key")
    app.set_llm_provider(llm)

    # 创建 Agent
    config = AgentConfig(
        agent_id="assistant",
        name="智能助手",
        system_prompt="你是一个专业、友好的 AI 助手。",
    )
    agent = app.create_agent(config)

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
