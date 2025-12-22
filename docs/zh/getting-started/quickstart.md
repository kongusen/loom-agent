# 快速上手

欢迎来到 Loom！本指南将带您在几分钟内构建您的第一个智能 Agent。

## 前置条件

- Python 3.9 或更高版本
- 一个可用的大模型 API Key (OpenAI, DeepSeek, Anthropic 等)

## 1. 安装

```bash
pip install loom-agent
```

## 2. 您的第一个 Agent

创建一个名为 `app.py` 的文件：

```python
import asyncio
from loom.builtin import Agent, OpenAILLM, tool

# 1. 定义一个工具
@tool
async def get_weather(city: str) -> str:
    """获取指定城市的天气信息。"""
    return f"{city} 的天气是晴朗，25°C"

async def main():
    # 2. 配置 LLM (Class-First 模式)
    # 推荐使用 OpenAILLM, DeepSeekLLM, ClaudeLLM 等显式类
    llm = OpenAILLM(api_key="sk-...", model="gpt-4o-mini")

    # 3. 创建 Agent
    agent = Agent(
        name="WeatherBot",
        llm=llm,
        tools=[get_weather],
        system_prompt="你是一个乐于助人的天气助手。"
    )

    # 4. 运行
    response = await agent.invoke("东京的天气怎么样？")
    print(response.content)

if __name__ == "__main__":
    asyncio.run(main())
```

## 3. 核心概念

- **Class-First 配置**: 我们显式实例化了 `OpenAILLM`。对于其他提供商，请使用 `DeepSeekLLM` 或 `ClaudeLLM`。这种方式提供了更好的代码提示。
- **@tool 装饰器**: 只需一个装饰器，即可将异步函数转换为 AI 可用的工具。必须包含类型提示 (Type Hints)！
- **Agent**: 核心协调者，负责管理 "思考" (LLM) 和 "行动" (Tools) 的循环。

## 下一步

- [配置指南](../guides/configuration.md): 了解支持的 LLM 列表及详细配置。
- [工具系统](../guides/tools.md): 学习构建更复杂的工具。
- [组合模式](../guides/patterns.md): 构建复杂工作流。
