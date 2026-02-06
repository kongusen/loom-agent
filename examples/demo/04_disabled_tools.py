"""
04_disabled_tools.py - 禁用内置工具

演示：
- AgentConfig.disabled_tools 禁用内置元工具
- 避免 delegate_task 等工具导致的递归问题
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from loom.agent import Agent
from loom.config.agent import AgentConfig
from loom.providers.llm import OpenAIProvider
from loom.config.llm import LLMConfig
from loom.tools.core.converters import FunctionToMCP
from loom.tools.core.registry import ToolRegistry

# 加载 .env 文件
load_dotenv(Path(__file__).parent.parent.parent / ".env")


async def my_tool(query: str) -> str:
    """我的自定义工具"""
    return f"处理: {query}"


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

    # 2. 配置禁用的内置工具
    agent_config = AgentConfig(
        disabled_tools={
            'create_plan',
            'delegate_task',
            'query_memory',
            'create_tool',
        }
    )

    # 3. 创建工具注册表并注册工具
    tool_registry = ToolRegistry()
    tool_registry.register_function(my_tool)
    tools = [FunctionToMCP.to_openai_format(my_tool)]

    # 4. 创建 Agent
    agent = Agent.create(
        llm=llm,
        tools=tools,
        tool_registry=tool_registry,
        config=agent_config,
        system_prompt="你是一个简单的助手。当用户要求处理内容时，使用 my_tool 工具。",
        max_iterations=5,
    )

    # 5. 验证工具列表
    tool_names = [
        t.get("function", {}).get("name")
        for t in agent.all_tools
        if isinstance(t, dict)
    ]
    print(f"可用工具: {tool_names}")

    # 6. 运行任务
    result = await agent.run("使用工具处理: hello")
    print(f"结果: {result}")


if __name__ == "__main__":
    asyncio.run(main())
