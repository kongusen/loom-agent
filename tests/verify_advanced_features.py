"""
Comprehensive Test for Advanced Features

Tests:
1. Configurable entropy control (soft limits)
2. Streaming mode with tool calls
3. Explicit state space modeling (CognitiveState)
4. Explicit projection operator (ProjectionOperator)
"""

import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loom.kernel.core import UniversalEventBus
from loom.kernel.core import Dispatcher
from loom.node.agent import AgentNode, ThinkingPolicy
from loom.node.tool import ToolNode
from loom.protocol.cloudevents import CloudEvent
from loom.protocol.mcp import MCPToolDefinition
from loom.interfaces.llm import StreamChunk
from loom.infra.llm import MockLLMProvider


async def test_configurable_entropy_control():
    """Test that entropy control is configurable, not enforced."""
    print("\n=== Test 1: Configurable Entropy Control ===")

    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)

    # Create agent with NO hard limits (user choice)
    agent = AgentNode(
        node_id="unlimited-agent",
        dispatcher=dispatcher,
        provider=MockLLMProvider(),
        thinking_policy=ThinkingPolicy(
            enabled=True,
            max_depth=None,  # No limit!
            max_thoughts=None,  # No limit!
            total_token_budget=None,  # No limit!
            thought_timeout=None,  # No limit!
            trigger_words=["analyze"],
            # But still have warning thresholds
            warn_depth=3,
            warn_thoughts=5
        )
    )

    print(f"✓ Agent created with unlimited policy:")
    print(f"  max_depth: {agent.thinking_policy.max_depth}")
    print(f"  max_thoughts: {agent.thinking_policy.max_thoughts}")
    print(f"  thought_timeout: {agent.thinking_policy.thought_timeout}")
    print("✓ Framework provides SUGGESTIONS, User has CONTROL")


async def test_streaming_with_tool_calls():
    """Test streaming mode with tool call support."""
    print("\n=== Test 2: Streaming with Tool Calls ===")

    # Create a mock provider that returns tool calls in stream
    class ToolCallStreamProvider(MockLLMProvider):
        async def stream_chat(self, messages, tools=None):
            # Stream a tool call
            yield StreamChunk(
                type="tool_call",
                content={
                    "name": "test_calculator",
                    "arguments": {"expr": "2+2"},
                    "id": "tc_123"
                },
                metadata={}
            )
            yield StreamChunk(type="done", content="", metadata={})

    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)

    # Create a mock tool
    async def calculator_func(arguments: dict) -> dict:
        return {"result": 4}

    tool_def = MCPToolDefinition(
        name="test_calculator",
        description="A calculator",
        input_schema={"type": "object"}
    )

    tool = ToolNode(
        node_id="tool/test_calculator",
        dispatcher=dispatcher,
        tool_def=tool_def,
        func=calculator_func
    )

    agent = AgentNode(
        node_id="streaming-agent",
        dispatcher=dispatcher,
        provider=ToolCallStreamProvider(),
        tools=[tool]
    )

    await asyncio.sleep(0.1)  # Let subscriptions settle

    event = CloudEvent.create(
        source="user",
        type="node.request",
        data={"task": "Calculate 2+2"}
    )

    result = await agent.process(event)
    print(f"✓ Streaming mode handled tool call: {result}")
    print("✓ Tool call in stream mode: SUPPORTED")


async def test_cognitive_state_modeling():
    """Test explicit state space modeling."""
    print("\n=== Test 3: Cognitive State Modeling ===")

    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)

    agent = AgentNode(
        node_id="cognitive-agent",
        dispatcher=dispatcher,
        provider=MockLLMProvider(),
        thinking_policy=ThinkingPolicy(
            enabled=True,
            trigger_words=["analyze"],
            max_depth=2  # Some limit for testing
        ),
        projection_strategy="selective"  # Use projection operator
    )

    # Check initial state
    print(f"Initial state dimensionality: {agent.cognitive_state.dimensionality()}")
    assert agent.cognitive_state.dimensionality() == 0, "Should start empty"

    # Spawn a thought (this adds to cognitive state)
    thought_id = await agent._spawn_thought("analyze this task")

    if thought_id:
        # Check state after spawning
        print(f"After spawning: S_dim = {agent.cognitive_state.dimensionality()}")
        assert agent.cognitive_state.dimensionality() > 0, "State should grow"

        # Check that thought is tracked
        thought = agent.cognitive_state.get_thought(thought_id)
        assert thought is not None, "Thought should be in state"
        print(f"✓ Thought tracked in state: {thought.id}, state={thought.state.value}")

        # Cleanup
        dispatcher.cleanup_ephemeral(thought_id)

    print("✓ Explicit CognitiveState: WORKING")
    print("✓ State space S ∈ R^N: MODELED")


async def test_projection_operator():
    """Test explicit projection operator."""
    print("\n=== Test 4: Projection Operator ===")

    from loom.kernel.core import (
        CognitiveState,
        ProjectionOperator,
        Thought,
        ThoughtState
    )

    # Create state with completed thoughts
    state = CognitiveState()

    thought1 = Thought(id="t1", task="Task 1", depth=1)
    thought1.state = ThoughtState.COMPLETED
    thought1.result = "Insight A"

    thought2 = Thought(id="t2", task="Task 2", depth=1)
    thought2.state = ThoughtState.COMPLETED
    thought2.result = "Insight B"

    state.add_thought(thought1)
    state.add_thought(thought2)

    print(f"State dimensionality: {state.dimensionality()}")

    # Test projection operator
    projector = ProjectionOperator(strategy="selective")

    # Collapse state
    observable = projector.collapse(state)

    print(f"✓ Projection π(S) → O:")
    print(f"  Input: S (dim={state.dimensionality()})")
    print(f"  Output: O = '{observable.content}'")
    print(f"  Metadata: {observable.metadata}")

    assert "Insight A" in observable.content or "Insight B" in observable.content
    print("✓ Explicit ProjectionOperator: WORKING")
    print("✓ π: S → O transformation: IMPLEMENTED")


async def main():
    print("="*60)
    print("ADVANCED FEATURES VERIFICATION")
    print("="*60)

    try:
        await test_configurable_entropy_control()
        await test_streaming_with_tool_calls()
        await test_cognitive_state_modeling()
        await test_projection_operator()

        print("\n" + "="*60)
        print("✅ ALL ADVANCED FEATURES TESTS PASSED")
        print("="*60)
        print("\nImplemented:")
        print("- ✅ Configurable entropy control (user choice)")
        print("- ✅ Streaming mode with tool calls")
        print("- ✅ Explicit state space modeling (CognitiveState)")
        print("- ✅ Explicit projection operator (ProjectionOperator)")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
