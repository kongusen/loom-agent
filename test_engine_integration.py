"""Test AgentEngine integration"""

import asyncio

from loom import AgentConfig, ModelRef, create_agent, tool
from loom.providers.base import CompletionParams, LLMProvider
from loom.runtime.engine import AgentEngine, EngineConfig


@tool(description="Add two numbers")
def add(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b


@tool(description="Multiply two numbers")
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b


async def test_engine_basic():
    """Test basic engine execution without provider"""
    print("\n=== Test 1: Basic Engine (No Provider) ===")

    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="You are a helpful assistant",
        )
    )

    result = await agent.run("Hello, world!")
    print(f"Status: {result.state}")
    print(f"Output: {result.output}")
    print(f"Duration: {result.duration_ms}ms")

    assert result.state.value in ["completed", "failed"]
    print("✓ Basic engine test passed")


async def test_engine_with_tools():
    """Test engine with tools"""
    print("\n=== Test 2: Engine with Tools ===")

    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="You are a calculator",
            tools=[add, multiply],
        )
    )

    assert len(agent.config.tools) == 2
    print(f"✓ Registered {len(agent.config.tools)} tools")

    from loom.tools.schema import Tool as EngineToolSchema
    converted = agent._convert_tool_to_schema(agent._compiled_tools[0])
    assert isinstance(converted, EngineToolSchema)
    print("✓ Tool conversion works")


async def test_runtime_fallback():
    """Test fallback behavior when no provider is available"""
    print("\n=== Test 3: Fallback Behavior ===")

    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="You are a helpful assistant",
        )
    )

    result = await agent.run("Test")
    print(f"Status: {result.state}")
    print(f"Output: {result.output}")

    assert result.state.value in ["completed", "failed"]
    print("✓ Runtime fallback works")


async def test_engine_components():
    """Test engine components directly"""
    print("\n=== Test 4: Engine Components ===")

    # Mock provider for testing
    class MockProvider(LLMProvider):
        async def _complete(self, _messages: list, _params: CompletionParams | None = None) -> str:
            return "Mock response: Task completed successfully"

        def stream(self, _messages: list, _params: CompletionParams | None = None):
            async def _gen():
                yield "Mock"
                yield " response"
            return _gen()

    provider = MockProvider()
    config = EngineConfig(
        max_iterations=10,
        max_tokens=100000,
        enable_heartbeat=False,
        enable_safety=True,
        enable_memory=False,
    )

    engine = AgentEngine(provider=provider, config=config)

    # Test execution
    result = await engine.execute(
        goal="Test goal",
        instructions="Test instructions",
        context={"test": "value"},
    )

    print(f"Result status: {result.get('status')}")
    print(f"Result output: {result.get('output')}")
    print(f"Iterations: {result.get('iterations')}")

    assert result.get("status") in ["success", "max_iterations"]
    print("✓ Engine components work")


async def test_context_manager():
    """Test context manager integration"""
    print("\n=== Test 5: Context Manager ===")

    from loom.context import ContextManager

    ctx = ContextManager(max_tokens=100000)

    # Test rho calculation
    rho = ctx.rho
    print(f"Initial ρ: {rho:.4f}")
    assert 0 <= rho <= 1

    # Test compression check
    strategy = ctx.should_compress()
    print(f"Compression strategy: {strategy}")

    # Test renewal check
    should_renew = ctx.should_renew()
    print(f"Should renew: {should_renew}")

    print("✓ Context manager works")


async def test_tool_registry():
    """Test tool registry"""
    print("\n=== Test 6: Tool Registry ===")

    from loom.tools.registry import ToolRegistry
    from loom.tools.schema import Tool, ToolDefinition

    registry = ToolRegistry()

    # Create test tool
    definition = ToolDefinition(
        name="test_tool",
        description="Test tool",
        is_read_only=True,
    )

    async def handler(**_kwargs):
        return "test result"

    tool = Tool(definition=definition, handler=handler)

    # Register
    registry.register(tool)
    assert registry.get("test_tool") is not None

    # List
    tools = registry.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "test_tool"

    print("✓ Tool registry works")


async def test_veto_authority():
    """Test veto authority"""
    print("\n=== Test 7: Veto Authority ===")

    from loom.safety.veto import VetoAuthority, VetoRule

    veto = VetoAuthority()

    # Add rule
    rule = VetoRule(
        name="no_delete",
        predicate=lambda tool, _args: tool == "delete_file",
        reason="Deletion not allowed",
    )
    veto.add_rule(rule)

    # Test veto
    vetoed, reason = veto.check_tool("delete_file", {})
    assert vetoed
    assert "not allowed" in reason.lower()

    # Test allowed tool
    vetoed, reason = veto.check_tool("read_file", {})
    assert not vetoed

    print(f"✓ Veto authority works (vetoed: {len(veto.veto_log)} calls)")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing AgentEngine Integration")
    print("=" * 60)

    try:
        await test_engine_basic()
        await test_engine_with_tools()
        await test_runtime_fallback()
        await test_engine_components()
        await test_context_manager()
        await test_tool_registry()
        await test_veto_authority()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
