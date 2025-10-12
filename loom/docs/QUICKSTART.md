# Loom 快速开始指南

## 安装

### 1. 克隆仓库

```bash
git clone <repository-url>
cd loom
```

### 2. 安装依赖

```bash
# 基础依赖
pip install -e .

# 可选依赖 (根据需要安装)
pip install openai             # OpenAI LLM
pip install anthropic          # Anthropic Claude
pip install httpx              # HTTP 请求工具
pip install duckduckgo-search  # Web 搜索
```

## 5 分钟上手

### 示例 1: 最简单的 Agent（推荐，一行构建）

创建 `hello_agent.py`:

```python
import asyncio
import loom
from loom.builtin.llms import MockLLM
from loom.builtin.memory import InMemoryMemory

async def main():
    # 一行创建 Agent（便捷构建）
    agent = loom.agent(llm=MockLLM(responses=["Hello! I'm a Loom agent."]),
                       memory=InMemoryMemory())
    result = await agent.ainvoke("Hi, who are you?")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

运行:
```bash
python hello_agent.py
```

### 示例 2: 带工具的 Agent（无外部依赖）

创建 `calculator_agent.py`:

```python
import asyncio, loom
from loom.builtin.llms import RuleLLM
from loom.builtin.tools import Calculator

async def main():
    agent = loom.agent(llm=RuleLLM(), tools=[Calculator()])
    result = await agent.ainvoke("Calculate 123 * 456")
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

运行:
```bash
python calculator_agent.py
```

### 示例 3: OpenAI Agent（需要 API key）

创建 `openai_agent.py`:

```python
import asyncio, loom
from loom.builtin.tools import Calculator, ReadFileTool, WriteFileTool

async def main():
    # 从环境变量读取 OPENAI_API_KEY
    agent = loom.agent(
        provider="openai", model="gpt-4o", temperature=0.7,
        tools=[Calculator(), ReadFileTool(), WriteFileTool()],
        max_iterations=10
    )

    tasks = [
        "Calculate 100 + 200",
        "Write the result to result.txt",
        "Read result.txt to verify"
    ]
    for task in tasks:
        print(f"\nTask: {task}")
        result = await agent.ainvoke(task)
        print(f"Result: {result}")

    print("\nMetrics:", agent.get_metrics())

if __name__ == "__main__":
    asyncio.run(main())
```

也可以使用 `agent_from_env()`，只需要设置 `LOOM_PROVIDER` 与 `LOOM_MODEL`：

```bash
export OPENAI_API_KEY="your-api-key"
export LOOM_PROVIDER=openai
export LOOM_MODEL=gpt-4o
```

```python
import asyncio, loom

async def main():
    agent = loom.agent_from_env()
    print(await agent.ainvoke("Say hello and compute 12*7"))

if __name__ == "__main__":
    asyncio.run(main())
```

设置环境变量并运行:
```bash
export OPENAI_API_KEY="your-api-key"
python openai_agent.py
```

### 示例 4: 流式输出

创建 `streaming_agent.py`:

```python
import asyncio, loom
from loom.builtin.tools import Calculator

async def main():
    agent = loom.agent(provider="openai", model="gpt-4o", tools=[Calculator()])

    print("Streaming output:\n")
    async for event in agent.astream("Tell me a joke and calculate 7 * 8"):
        if event.type == "text_delta":
            print(event.content, end="", flush=True)
        elif event.type == "tool_calls_start":
            print(f"\n[Calling tools: {[tc.name for tc in event.tool_calls]}]")
        elif event.type == "tool_result":
            print(f"[Result: {event.result.content[:50]}]")
        elif event.type == "agent_finish":
            print("\n[Done]")

if __name__ == "__main__":
    asyncio.run(main())
```

### 示例 5: Multi-Agent 系统

创建 `multi_agent.py`:

```python
import asyncio
import os
from loom import Agent
from loom.builtin.llms import OpenAILLM
from loom.builtin.tools import Calculator, ReadFileTool, WriteFileTool
from loom.patterns import MultiAgentSystem

async def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Please set OPENAI_API_KEY")
        return

    # 创建专业 Agent
    researcher = Agent(
        llm=OpenAILLM(api_key=api_key, model="gpt-4", temperature=0.3),
        tools=[ReadFileTool()]
    )

    analyst = Agent(
        llm=OpenAILLM(api_key=api_key, model="gpt-4", temperature=0.5),
        tools=[Calculator()]
    )

    writer = Agent(
        llm=OpenAILLM(api_key=api_key, model="gpt-4", temperature=0.7),
        tools=[WriteFileTool()]
    )

    # 创建协调器
    coordinator = OpenAILLM(api_key=api_key, model="gpt-4")

    # 创建系统
    system = MultiAgentSystem(
        agents={
            "researcher": researcher,
            "analyst": analyst,
            "writer": writer
        },
        coordinator=coordinator
    )

    # 执行复杂任务
    result = await system.run(
        "Research Python trends, analyze popularity, write report"
    )
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## 更多示例

查看 `examples/` 目录下的完整示例:

- `loom_quickstart.py` - 最简单的示例
- `openai_agent_example.py` - OpenAI Agent 完整示例
- `multi_agent_example.py` - Multi-Agent 系统
- `code_agent_with_tools.py` - 代码助手 Agent
- `loom_tools_loop.py` - 工具循环示例

## 下一步

1. 阅读 [完整文档](./README_LOOM.md)
2. 查看 [MCP 集成](./LOOM_MCP_INTEGRATION.md)
3. 了解 [回调与事件规范](./CALLBACKS_SPEC.md)
4. 自定义你的工具和 LLM

## 常见问题

### Q: 我需要 API key 吗?

A: 不一定。你可以使用内置的 `MockLLM` 和 `RuleLLM` 进行开发和测试,无需 API key。生产环境建议使用 `OpenAILLM` 或其他 LLM 提供者。

### Q: 如何添加自定义工具?

A: 使用装饰器 `@loom.tool` 或继承 `BaseTool`：

```python
import loom
from typing import List

@loom.tool(description="Sum a list of numbers")
def sum_list(nums: List[float]) -> float:
    return sum(nums)

SumTool = sum_list
agent = loom.agent(provider="openai", model="gpt-4o", tools=[SumTool()])
```

### Q: 如何调试 Agent?

A: 使用流式输出和指标:

```python
# 流式输出查看执行过程
async for event in agent.stream(input):
    print(event)

# 查看指标
metrics = agent.get_metrics()
print(metrics)
```

### Q: 如何控制权限?

A: 在创建 Agent 时设置权限策略:

```python
agent = Agent(
    llm=llm,
    tools=tools,
    permission_policy={
        "write_file": "ask",   # 需要确认
        "http_request": "deny", # 拒绝
        "default": "allow"      # 默认允许
    }
)
```

## 获取帮助

- 查看文档: `./docs/`
- 提交 Issue: GitHub Issues
- 加入讨论: Discussions

---

Happy coding with Loom! 🧩
