"""
Loom v0.1.6 - 简单示例

展示新架构的核心特性：
1. @tool 装饰器定义工具
2. SimpleAgent 基础用法
3. 递归状态机执行
"""

import asyncio
import loom, Message, tool
from loom.builtin import OpenAILLM


# ============================================================================
# 1. 定义工具 - 使用 @tool 装饰器
# ============================================================================

@tool(name="calculator", description="Perform mathematical calculations")
async def calculator(expression: str) -> float:
    """
    计算数学表达式

    Args:
        expression: 数学表达式，如 "2+2"

    Returns:
        计算结果
    """
    try:
        # 注意：实际生产环境不应使用 eval，这里仅作演示
        result = eval(expression)
        return float(result)
    except Exception as e:
        return f"Error: {str(e)}"


@tool(name="get_weather", description="Get weather information for a city")
async def get_weather(city: str) -> str:
    """
    获取城市天气（模拟）

    Args:
        city: 城市名称

    Returns:
        天气信息
    """
    # 模拟天气数据
    weather_data = {
        "Beijing": "Sunny, 25°C",
        "Shanghai": "Cloudy, 22°C",
        "Guangzhou": "Rainy, 28°C",
    }
    return weather_data.get(city, f"Weather data not available for {city}")


# ============================================================================
# 2. 创建 Agent
# ============================================================================

async def main():
    """主函数"""

    # 创建 SimpleAgent
    agent = loom.agent(
        name="assistant",
        llm=OpenAILLM(
            api_key="your-api-key-here",  # 替换为真实 API key
            model="gpt-4",
        ),
        tools=[calculator, get_weather],
        system_prompt="You are a helpful assistant with access to calculator and weather tools.",
    )

    print("=" * 80)
    print("Loom v0.1.6 - Simple Example")
    print("=" * 80)
    print()

    # ========================================================================
    # 示例 1: 简单对话
    # ========================================================================
    print("Example 1: Simple Conversation")
    print("-" * 80)

    message1 = Message(role="user", content="Hello! What can you do?")
    response1 = await agent.run(message1)

    print(f"User: {message1.content}")
    print(f"Assistant: {response1.content}")
    print()

    # ========================================================================
    # 示例 2: 工具调用 - 计算器
    # ========================================================================
    print("Example 2: Tool Use - Calculator")
    print("-" * 80)

    message2 = Message(role="user", content="What is 123 * 456?")
    response2 = await agent.run(message2)

    print(f"User: {message2.content}")
    print(f"Assistant: {response2.content}")
    print()

    # ========================================================================
    # 示例 3: 工具调用 - 天气查询
    # ========================================================================
    print("Example 3: Tool Use - Weather")
    print("-" * 80)

    message3 = Message(role="user", content="What's the weather like in Beijing?")
    response3 = await agent.run(message3)

    print(f"User: {message3.content}")
    print(f"Assistant: {response3.content}")
    print()

    # ========================================================================
    # 示例 4: 多轮对话（带历史）
    # ========================================================================
    print("Example 4: Multi-turn Conversation")
    print("-" * 80)

    # 第一轮
    msg4_1 = Message(role="user", content="Calculate 100 + 200")
    resp4_1 = await agent.run(msg4_1)
    print(f"User: {msg4_1.content}")
    print(f"Assistant: {resp4_1.content}")

    # 第二轮（带历史）
    msg4_2 = Message(
        role="user",
        content="Now multiply that result by 2"
    ).with_history([msg4_1, resp4_1])

    resp4_2 = await agent.run(msg4_2)
    print(f"User: {msg4_2.content}")
    print(f"Assistant: {resp4_2.content}")
    print()

    # ========================================================================
    # 示例 5: 统计信息
    # ========================================================================
    print("Example 5: Agent Stats")
    print("-" * 80)

    stats = agent.get_stats()
    print(f"Agent Stats: {stats}")
    print()

    print("=" * 80)
    print("All examples completed!")
    print("=" * 80)


# ============================================================================
# 运行示例
# ============================================================================

if __name__ == "__main__":
    # 注意：你需要设置 OPENAI_API_KEY 环境变量或在代码中提供 API key
    asyncio.run(main())
