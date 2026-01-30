"""
Test Tool Creation - Verify dynamic tool creation capability

This script tests:
1. Agent can create tools dynamically
2. Agent can use created tools
3. Output repetition is fixed
"""

import asyncio
import os

from loom.config.llm import LLMConfig
from loom.events import EventBus
from loom.orchestration.agent import Agent
from loom.protocol import Task
from loom.providers.llm.openai import OpenAIProvider


async def main() -> None:
    # Setup LLM provider
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Missing OPENAI_API_KEY in environment.")
        return

    config = LLMConfig(
        provider="openai",
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL"),
        temperature=0.7,
    )
    llm_provider = OpenAIProvider(config)

    # Create event bus
    event_bus = EventBus()

    # Create agent with tool creation enabled
    agent = Agent(
        node_id="test-agent",
        llm_provider=llm_provider,
        system_prompt=(
            "You are a helpful assistant that can create and use tools. "
            "When you are done, call the 'done' tool."
        ),
        event_bus=event_bus,
        require_done_tool=True,
        enable_tool_creation=True,
        max_iterations=10,
    )

    print("=== Test 1: Tool Creation Capability ===\n")

    # Test 1: Ask agent to create a tool
    task1 = Task(
        task_id="test-1",
        action="execute",
        parameters={
            "content": (
                "请创建一个名为 'calculate_factorial' 的工具，"
                "用于计算阶乘。然后使用这个工具计算 5 的阶乘。"
            )
        },
    )

    print("Task: 创建并使用阶乘计算工具\n")
    result1 = await agent.execute_task(task1)

    if result1.result:
        content = (
            result1.result.get("content", "")
            if isinstance(result1.result, dict)
            else str(result1.result)
        )
        print(f"\nResult: {content}\n")

    print("\n=== Test 2: Simple Question (No Repetition) ===\n")

    # Test 2: Simple question to verify no repetition
    task2 = Task(
        task_id="test-2",
        action="execute",
        parameters={"content": "你好，你可以自主构建工具么？"},
    )

    print("Task: 测试输出是否重复\n")
    result2 = await agent.execute_task(task2)

    if result2.result:
        content = (
            result2.result.get("content", "")
            if isinstance(result2.result, dict)
            else str(result2.result)
        )
        print(f"\nResult: {content}\n")

        # Check for repetition
        sentences = content.split("。")
        unique_sentences = {s.strip() for s in sentences if s.strip()}
        if len(sentences) > len(unique_sentences) + 2:
            print("⚠️  Warning: Possible repetition detected")
        else:
            print("✓ No repetition detected")

    print("\n=== Tests Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
