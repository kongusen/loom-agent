"""Demo 04: 工作状态 - L2 能力

展示 WorkingState 的使用。
"""

import asyncio
from loom.agent import Agent
from loom.providers.llm.openai import OpenAIProvider


async def main():
    provider = OpenAIProvider(api_key="your-key")
    agent = Agent(provider=provider)

    # 设置工作状态
    agent.working_state.goal = "分析数据"
    agent.working_state.plan = "1. 读取文件\n2. 处理数据\n3. 生成报告"
    agent.working_state.next_action = "读取数据文件"

    print("=== 工作状态 ===")
    print(f"目标: {agent.working_state.goal}")
    print(f"计划: {agent.working_state.plan}")
    print(f"下一步: {agent.working_state.next_action}")

    # 转换为文本
    text = agent.working_state.to_text(agent.tokenizer)
    print(f"\n文本表示:\n{text}")


if __name__ == "__main__":
    asyncio.run(main())
