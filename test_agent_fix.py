"""Test the fixed Agent.run() implementation"""

import asyncio
from loom.agent import Agent
from loom.agent.runtime import RuntimeConfig
from loom.providers.openai import OpenAIProvider
from loom.tools import ToolRegistry
from loom.tools.schema import Tool, ToolDefinition, ToolParameter


async def simple_calculator(operation: str, a: float, b: float) -> str:
    """Simple calculator tool"""
    if operation == "add":
        return str(a + b)
    elif operation == "subtract":
        return str(a - b)
    elif operation == "multiply":
        return str(a * b)
    elif operation == "divide":
        return str(a / b) if b != 0 else "Error: Division by zero"
    return "Unknown operation"


async def test_agent_run():
    """Test that Agent.run() actually executes"""

    # Create a mock provider for testing
    class MockProvider:
        async def complete(self, messages, params=None):
            # Simulate LLM response
            return "I will calculate 5 + 3. The answer is 8. Task completed."

        async def stream(self, messages, params=None):
            yield "Mock stream"

    # Setup
    provider = MockProvider()
    config = RuntimeConfig(
        max_tokens=100000,
        max_depth=3,
        system_prompt="You are a helpful calculator assistant."
    )

    # Create tool registry
    tool_registry = ToolRegistry()
    calc_tool = Tool(
        definition=ToolDefinition(
            name="calculator",
            description="Perform basic arithmetic",
            parameters=[
                ToolParameter("operation", "string", "Operation: add, subtract, multiply, divide"),
                ToolParameter("a", "number", "First number"),
                ToolParameter("b", "number", "Second number"),
            ]
        ),
        handler=simple_calculator
    )
    tool_registry.register(calc_tool)

    # Create agent
    agent = Agent(provider, config, tool_registry)

    # Run agent
    result = await agent.run("Calculate 5 + 3", max_steps=5)

    print("=" * 60)
    print("Agent Run Result:")
    print("=" * 60)
    print(result)
    print("=" * 60)
    print(f"Turn count: {agent._turn_count}")
    print(f"Context rho: {agent.context.rho:.3f}")
    print(f"History messages: {len(agent.context.partitions.history)}")
    print("=" * 60)

    # Verify that execution actually happened
    assert agent._turn_count > 0, "Agent should have made at least one turn"
    assert len(agent.context.partitions.history) > 0, "History should have messages"
    assert result != "", "Result should not be empty"

    print("\n✅ Test passed! Agent.run() is now functional.")


if __name__ == "__main__":
    asyncio.run(test_agent_run())
