# 快速开始

## 安装

```bash
pip install loom-agent
```

## 基础概念

Loom 是一个基于公理系统的 AI Agent 框架：

- **公理系统**: 5条基础公理确保逻辑一致性
- **分形架构**: O(1) 认知负载的递归组合
- **代谢记忆**: L1-L4 完整记忆谱系
- **事件总线**: 类型安全的分布式通信
- **四范式**: Reflection/Tool/Planning/Collaboration

## 五分钟上手

### 1. 创建 Agent

```python
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider

llm = OpenAIProvider(api_key="your-api-key")

agent = Agent.create(
    llm,
    node_id="assistant",
    system_prompt="你是一个友好的助手。"
)
```

### 2. 执行任务

```python
from loom.protocol import Task

task = Task(
    task_id="task-1",
    action="chat",
    parameters={"content": "你好"}
)

result = await agent.execute_task(task)
print(result.result)
```

### 3. 流式输出

```python
async for chunk in agent.stream_thinking():
    if chunk.type == "text":
        print(chunk.content, end="", flush=True)
```

## 下一步

- [Agent API](API-Agent)
- [快速开始示例](examples/Quick-Start)
- [研究小组示例](examples/Research-Team)

## 反向链接

被引用于: [Home](Home)
