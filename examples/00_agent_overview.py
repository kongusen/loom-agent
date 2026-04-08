"""Public Agent API examples."""

import asyncio
import os

from loom import (
    AgentConfig,
    KnowledgeDocument,
    KnowledgeSource,
    ModelRef,
    SessionConfig,
    create_agent,
    tool,
)


# ============================================================
# 示例 1: 最简单的 agent
# ============================================================
async def example_basic():
    """最基础的用法 - 无工具"""
    print("\n=== Example 1: Basic Agent ===")

    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="你是一个友好的助手",
        )
    )

    result = await agent.run("2+2等于多少？")
    print(f"Output: {result.output}")


# ============================================================
# 示例 2: 带自定义工具的 agent
# ============================================================
@tool(description="搜索文档")
async def search_docs(query: str) -> str:
    """搜索文档数据库"""
    # 模拟搜索
    return f"找到关于 '{query}' 的 3 条结果"


@tool(description="计算数学表达式", read_only=True)
def calculate(expression: str) -> str:
    """安全计算数学表达式"""
    try:
        # 注意：生产环境应该使用更安全的方式
        result = eval(expression, {"__builtins__": {}}, {})
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算错误: {e}"


async def example_with_tools():
    """带工具的 agent"""
    print("\n=== Example 2: Agent with Tools ===")

    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="你是一个代码助手，可以搜索文档和计算",
            tools=[search_docs, calculate],
        )
    )

    result = await agent.run("搜索关于 asyncio 的文档")
    print(f"Output: {result.output}")


# ============================================================
# 示例 2.5: 带知识源的 agent
# ============================================================
async def example_with_knowledge():
    """带知识源的 agent"""
    print("\n=== Example 2.5: Agent with Knowledge ===")

    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="你是一个熟悉 Loom 的助手",
            knowledge=[
                KnowledgeSource.inline(
                    "loom-docs",
                    [
                        KnowledgeDocument(content="Loom 提供 stateful session API。", title="Session"),
                        KnowledgeDocument(content="Loom 支持 heartbeat 和 safety rule 配置。", title="Safety"),
                    ],
                    description="Loom product notes",
                )
            ],
        )
    )

    result = await agent.run("概括 Loom 的能力")
    print(f"Output: {result.output}")


# ============================================================
# 示例 3: 流式输出
# ============================================================
async def example_streaming():
    """流式输出事件"""
    print("\n=== Example 3: Streaming Events ===")

    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="你是一个助手",
        )
    )

    async for event in agent.stream("解释什么是 Python"):
        print(f"Event: {event.type} - {event.payload}")


# ============================================================
# 示例 4: 有状态的 session
# ============================================================
async def example_session():
    """多轮对话 session"""
    print("\n=== Example 4: Stateful Session ===")

    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="你是一个记得上下文的助手",
        )
    )

    # 创建 session
    session = agent.session(SessionConfig(id="user-123"))

    # 第一轮
    result1 = await session.run("我的名字是张三")
    print(f"Round 1: {result1.output}")

    # 第二轮 - agent 应该记得名字
    result2 = await session.run("我的名字是什么？")
    print(f"Round 2: {result2.output}")


# ============================================================
# 示例 5: 显式配置 agent
# ============================================================
async def example_explicit_configuration():
    """通过完整 AgentConfig 显式组装 agent"""
    print("\n=== Example 5: Explicit AgentConfig ===")

    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="你是一个增强的助手，可以搜索和计算",
            tools=[search_docs, calculate],
        )
    )

    result = await agent.run("计算 10 * 5")
    print(f"Output: {result.output}")


# ============================================================
# 示例 6: 直接控制 run 对象
# ============================================================
async def example_run_control():
    """直接创建 run 并消费事件流"""
    print("\n=== Example 6: Run Control ===")

    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="你是一个助手",
        )
    )

    session = agent.session(SessionConfig(id="advanced-session"))
    run = session.start("分析这个系统")

    # 订阅事件流
    async for event in run.events():
        print(f"Event: {event.type}")
        if event.type == "run.completed":
            break

    result = await run.wait()
    print(f"Output: {result.output}")


# ============================================================
# 示例 7: 不同的 provider
# ============================================================
async def example_providers():
    """使用不同的 LLM provider"""
    print("\n=== Example 7: Different Providers ===")

    providers = [
        create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                instructions="你是 Claude",
            )
        ),
        create_agent(
            AgentConfig(
                model=ModelRef.openai("gpt-4"),
                instructions="你是 GPT-4",
            )
        ),
        create_agent(
            AgentConfig(
                model=ModelRef.gemini("gemini-pro"),
                instructions="你是 Gemini",
            )
        ),
        create_agent(
            AgentConfig(
                model=ModelRef.ollama("llama3"),
                instructions="你是本地模型",
            )
        ),
    ]

    print(f"Created {len(providers)} agents with different providers")


# ============================================================
# 主函数
# ============================================================
async def main():
    """运行所有示例"""

    # 检查 API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("警告: ANTHROPIC_API_KEY 未设置，某些示例可能失败")
        print("设置方法: export ANTHROPIC_API_KEY=sk-ant-...")
        return

    # 运行示例
    await example_basic()
    await example_with_tools()
    await example_with_knowledge()
    # await example_streaming()  # 可能需要较长时间
    await example_session()
    await example_explicit_configuration()
    # await example_run_control()  # 进阶示例
    # await example_providers()  # 需要多个 API keys


if __name__ == "__main__":
    asyncio.run(main())
