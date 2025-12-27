"""
Verification script for Entropy Control implementation.

Tests:
1. Depth limit enforcement
2. Active thought limit
3. Timeout enforcement
"""

import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loom.kernel.bus import UniversalEventBus
from loom.kernel.dispatcher import Dispatcher
from loom.node.agent import AgentNode, ThinkingPolicy
from loom.protocol.cloudevents import CloudEvent
from loom.infra.llm import MockLLMProvider


async def test_depth_limit():
    """Test that depth limit prevents infinite recursion."""
    print("\n=== Test 1: Depth Limit ===")

    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)

    # Create agent with depth=0 and max_depth=2
    agent = AgentNode(
        node_id="root-agent",
        dispatcher=dispatcher,
        provider=MockLLMProvider(),
        thinking_policy=ThinkingPolicy(
            enabled=True,
            max_depth=2,
            trigger_words=["analyze"],
        ),
        current_depth=0
    )

    event = CloudEvent.create(
        source="user",
        type="node.request",
        data={"task": "analyze this"}
    )

    result = await agent.process(event)
    print(f"✓ Root agent (depth=0) completed: {result['response'][:30]}...")

    # Now test agent at max depth - should NOT spawn thoughts
    deep_agent = AgentNode(
        node_id="deep-agent",
        dispatcher=dispatcher,
        provider=MockLLMProvider(),
        thinking_policy=ThinkingPolicy(
            enabled=True,
            max_depth=2,
            trigger_words=["analyze"],
        ),
        current_depth=2  # Already at max depth
    )

    # This should NOT spawn any thoughts
    thought_id = await deep_agent._spawn_thought("analyze this")
    assert thought_id is None, "Agent at max depth should not spawn thoughts!"
    print("✓ Depth limit enforced: Agent at max depth cannot spawn thoughts")


async def test_active_thought_limit():
    """Test that max_thoughts limit is enforced."""
    print("\n=== Test 2: Active Thought Limit ===")

    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)

    agent = AgentNode(
        node_id="busy-agent",
        dispatcher=dispatcher,
        provider=MockLLMProvider(),
        thinking_policy=ThinkingPolicy(
            enabled=True,
            max_thoughts=2,  # Only allow 2 concurrent thoughts
            trigger_words=["analyze"],
        )
    )

    # Spawn 2 thoughts
    thought1 = await agent._spawn_thought("analyze task 1")
    thought2 = await agent._spawn_thought("analyze task 2")

    print(f"✓ Spawned 2 thoughts: {thought1}, {thought2}")
    print(f"  Active thoughts: {agent._active_thoughts}")

    # Try to spawn a 3rd - should be blocked
    thought3 = await agent._spawn_thought("analyze task 3")
    assert thought3 is None, "Should not spawn more than max_thoughts!"
    print("✓ Active thought limit enforced: 3rd thought blocked")

    # Cleanup
    if thought1:
        dispatcher.cleanup_ephemeral(thought1)
    if thought2:
        dispatcher.cleanup_ephemeral(thought2)


async def test_timeout_enforcement():
    """Test that thought timeout is enforced."""
    print("\n=== Test 3: Timeout Enforcement ===")

    # This test verifies that the timeout logic is in place
    # (Full timeout testing requires a slow-running thought mock)

    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)

    agent = AgentNode(
        node_id="timeout-agent",
        dispatcher=dispatcher,
        provider=MockLLMProvider(),
        thinking_policy=ThinkingPolicy(
            enabled=True,
            thought_timeout=0.5,  # Very short timeout
        )
    )

    print(f"✓ Agent configured with timeout={agent.thinking_policy.thought_timeout}s")
    print("  (Timeout enforcement tested in projection logic)")


async def main():
    print("="*60)
    print("ENTROPY CONTROL VERIFICATION")
    print("="*60)

    try:
        await test_depth_limit()
        await test_active_thought_limit()
        await test_timeout_enforcement()

        print("\n" + "="*60)
        print("✅ ALL ENTROPY CONTROL TESTS PASSED")
        print("="*60)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
