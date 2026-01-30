"""
Test script to verify plan execution fixes
"""

import asyncio
import os
from uuid import uuid4

from loom.config.llm import LLMConfig
from loom.events import EventBus
from loom.orchestration.agent import Agent
from loom.protocol import Task
from loom.providers.llm.openai import OpenAIProvider


async def main():
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

    # Setup event bus
    event_bus = EventBus()

    # Track events
    planning_events = []
    tool_call_events = []

    async def track_event(event_task: Task) -> Task:
        if event_task.action == "node.planning":
            planning_events.append(event_task)
            print(f"\n[PLANNING] Goal: {event_task.parameters.get('goal', '')}")
            print(f"           Steps: {len(event_task.parameters.get('steps', []))}")
        elif event_task.action == "node.tool_call":
            tool_name = event_task.parameters.get("tool_name", "")
            tool_call_events.append(event_task)
            if tool_name == "create_plan":
                print("[TOOL_CALL] create_plan")
        return event_task

    event_bus.register_handler("node.planning", track_event)
    event_bus.register_handler("node.tool_call", track_event)

    # Create agent
    agent = Agent(
        node_id="test-agent",
        llm_provider=llm_provider,
        system_prompt=(
            "You are a helpful assistant. "
            "When the user sends a message, think about your response and then call the 'done' tool. "
            "IMPORTANT: The 'content' parameter of the done tool must contain your ACTUAL response to the user."
        ),
        event_bus=event_bus,
        require_done_tool=True,
        enable_tool_creation=False,
        max_iterations=15,
        memory_config={
            "max_l1_size": 40,
            "max_l2_size": 12,
            "max_l3_size": 24,
        },
    )

    # Create test task
    session_id = f"test-session-{uuid4()}"
    task = Task(
        task_id=f"test-{uuid4()}",
        action="execute",
        parameters={"content": "一人公司如何去做，基于AI在软件行业有发展么"},
        session_id=session_id,
    )

    print("=" * 80)
    print("TEST: Plan Execution Fix")
    print("=" * 80)
    print(f"\nUser Question: {task.parameters['content']}")
    print("\n" + "-" * 80)

    # Execute task
    result = await agent.execute_task(task)

    # Print results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    print(f"\nStatus: {result.status.value}")
    print(f"Planning Events: {len(planning_events)}")
    print(f"Total Nodes Used: {len(agent.memory.get_l1_tasks())}")

    if result.result:
        content = (
            result.result.get("content", "")
            if isinstance(result.result, dict)
            else str(result.result)
        )
        print(f"\nFinal Answer Length: {len(content)} chars")
        print("\nFinal Answer Preview:")
        print("-" * 80)
        print(content[:500] + ("..." if len(content) > 500 else ""))
        print("-" * 80)

    # Check for nested planning
    print("\n[CHECK] Nested Planning:")
    if len(planning_events) > 1:
        print(f"  ⚠️  WARNING: {len(planning_events)} planning events detected (expected 1)")
        for idx, event in enumerate(planning_events, 1):
            print(f"    {idx}. {event.parameters.get('goal', '')[:60]}")
    else:
        print(f"  ✅ OK: Only {len(planning_events)} planning event")

    # Check answer quality
    print("\n[CHECK] Answer Quality:")
    if result.result:
        content = (
            result.result.get("content", "")
            if isinstance(result.result, dict)
            else str(result.result)
        )
        if "Plan" in content and "completed with" in content and "steps:" in content:
            print("  ⚠️  WARNING: Answer looks like a plan summary")
        elif "Step 1:" in content or "Step 2:" in content:
            print("  ⚠️  WARNING: Answer contains step-by-step format")
        else:
            print("  ✅ OK: Answer appears to be synthesized")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
