"""
02_custom_tools.py - 自定义工具

演示：
- ToolRegistry 注册工具
- FunctionToMCP.to_openai_format() 转换为 OpenAI 格式
- Agent 使用自定义工具
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider
from loom.config.llm import LLMConfig
from loom.tools.core.converters import FunctionToMCP
from loom.tools.core.registry import ToolRegistry

# 加载 .env 文件
load_dotenv(Path(__file__).parent.parent.parent / ".env")


# 定义自定义工具（异步函数）
async def calculate(expression: str) -> str:
    """计算数学表达式"""
    try:
        result = eval(expression)
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算错误: {e}"


async def get_weather(city: str) -> str:
    """获取城市天气（模拟）"""
    return f"{city}今天晴，温度 25°C"


async def main():
    # 1. 创建 LLM Provider（从环境变量获取配置）
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        print("请设置 OPENAI_API_KEY 环境变量")
        return

    config = LLMConfig(provider="openai", model=model, api_key=api_key, base_url=base_url)
    llm = OpenAIProvider(config)

    # 2. 创建工具注册表并注册工具
    tool_registry = ToolRegistry()
    tool_registry.register_function(calculate)
    tool_registry.register_function(get_weather)

    # 3. 获取 OpenAI 格式的工具定义
    tools = [FunctionToMCP.to_openai_format(calculate), FunctionToMCP.to_openai_format(get_weather)]

    print("注册的工具:")
    for name in tool_registry.tool_names:
        print(f"  - {name}")

    # 4. 创建 Agent（传入 tool_registry）
    agent = Agent.create(
        llm=llm,
        tools=tools,
        tool_registry=tool_registry,
        system_prompt="你是一个助手，可以计算和查询天气。当用户询问天气时，使用 get_weather 工具。",
        max_iterations=5,
    )

    # 5. 运行任务
    result = await agent.run("北京今天天气怎么样？")
    print(f"结果: {result}")


if __name__ == "__main__":
    asyncio.run(main())
