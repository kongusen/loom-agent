import asyncio

import pytest

from loom.config.fractal import FractalConfig, NodeRole
from loom.kernel.core import Dispatcher, UniversalEventBus
from loom.llm import MockLLMProvider
from loom.memory.core import LoomMemory
from loom.memory.types import ContextProjection, MemoryQuery, MemoryTier, MemoryType, MemoryUnit
from loom.node.fractal import FractalAgentNode


@pytest.fixture
def infrastructure():
    """Setup basic infrastructure."""
    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)
    provider = MockLLMProvider()
    return bus, dispatcher, provider

@pytest.mark.asyncio
async def test_hot_plug_lifecycle(infrastructure):
    """
    Test Scenario 1: Dynamic Hierarchy Construction (Hot-Plugging)
    - Create Root Agent
    - Dynamically Add Child
    - Verify Structure
    - Dynamically Remove Child
    """
    bus, dispatcher, provider = infrastructure

    # 1. Create Root Agent
    root_agent = FractalAgentNode(
        node_id="root-agent",
        dispatcher=dispatcher,
        provider=provider,
        role=NodeRole.COORDINATOR,
        fractal_config=FractalConfig(enabled=True)
    )

    assert len(root_agent.children) == 0
    print(f"\n✅ Root agent created: {root_agent.node_id}")

    # 2. Hot-plug Child
    print("🔌 Hot-plugging child node...")
    child_agent = root_agent.add_child(
        role=NodeRole.SPECIALIST,
        system_prompt="I am a dynamic specialist."
    )

    # 3. Verify Structure
    assert len(root_agent.children) == 1
    assert root_agent.children[0] == child_agent
    assert child_agent.parent == root_agent
    assert child_agent.depth == root_agent.depth + 1
    print(f"✅ Child added: {child_agent.node_id} (Depth: {child_agent.depth})")

    # 4. Remove Child
    print("🔌 Removing child node...")
    root_agent.remove_child(child_agent)

    assert len(root_agent.children) == 0
    print(f"✅ Child removed. Children count: {len(root_agent.children)}")


@pytest.mark.asyncio
async def test_memory_sharing_and_isolation(infrastructure):
    """
    Test Scenario 2: Memory Scope & Sharing
    - Shared Memory: L4 Global Knowledge is shared by default in manual composition
    - Isolation: L1 Local Thoughts are attributed to specific nodes
    """
    bus, dispatcher, provider = infrastructure

    # Shared Memory Instance
    shared_memory = LoomMemory(node_id="root-agent")

    # 1. Create Root with Shared Memory
    root_agent = FractalAgentNode(
        node_id="root-agent",
        dispatcher=dispatcher,
        provider=provider,
        memory=shared_memory,
        fractal_config=FractalConfig(enabled=True)
    )

    # 2. Parent learns Fact A (L4)
    print("\n📝 Parent learning Fact A...")
    await root_agent.memory.add(MemoryUnit(
        content="Fact A: The sky is blue.",
        tier=MemoryTier.L4_GLOBAL,
        type=MemoryType.FACT,
        importance=1.0,
        source_node=root_agent.node_id
    ))

    # Verify Parent sees it
    l4_units = await root_agent.memory.query(MemoryQuery(tiers=[MemoryTier.L4_GLOBAL]))
    fact_a = next((u for u in l4_units if "Fact A" in str(u.content)), None)
    assert fact_a is not None

    # 3. Hot-plug Child (Inherits Memory by default in add_child)
    print("🔌 Hot-plugging child with shared memory...")
    child_agent = root_agent.add_child(
        role=NodeRole.SPECIALIST,
        # add_child automatically passes self.memory if not overridden
    )
    assert child_agent.memory == root_agent.memory

    # 4. Child verifies Fact A (Access Shared L4)
    print("🔍 Child querying Fact A...")
    # Simulate child implementation reading memory
    child_view_l4 = await child_agent.memory.query(MemoryQuery(tiers=[MemoryTier.L4_GLOBAL]))
    child_found_fact = next((u for u in child_view_l4 if "Fact A" in str(u.content)), None)
    assert child_found_fact is not None
    print(f"✅ Child successfully accessed shared fact: {child_found_fact.content}")

    # 5. Child produces Thought B (L1 Local)
    print("💭 Child thinking...")
    thought_content = "Child Thought: I should analyze the color blue."
    await child_agent.memory.add(MemoryUnit(
        content=thought_content,
        tier=MemoryTier.L1_RAW_IO,
        type=MemoryType.THOUGHT,
        source_node=child_agent.node_id  # Explicit attribution
    ))

    # 6. Verify Attribution
    # Query all L1
    all_l1 = child_agent.memory._l1_buffer
    thought_unit = next((u for u in all_l1 if thought_content in str(u.content)), None)

    assert thought_unit is not None
    assert thought_unit.source_node == child_agent.node_id
    assert thought_unit.source_node != root_agent.node_id
    print(f"✅ Thought correctly attributed to Child ({thought_unit.source_node})")


@pytest.mark.asyncio
async def test_context_projection_init(infrastructure):
    """
    Test Scenario 3: Context Projection during Hot-Plug
    - Verify we can hot-plug a node initialized with a specific ContextProjection
    """
    bus, dispatcher, provider = infrastructure

    # Setup Projection
    projection = ContextProjection(
        instruction="Fix the bug in module X",
        lineage=["root-agent"],
        parent_plan="1. Analyze code\n2. Write test",
        relevant_facts=[
            MemoryUnit(content="Module X handles payments", tier=MemoryTier.L4_GLOBAL, type=MemoryType.FACT)
        ]
    )

    root_agent = FractalAgentNode(
        node_id="root-agent",
        dispatcher=dispatcher,
        provider=provider
    )

    print("\n🔌 Hot-plugging child with Context Projection...")

    # If we use standard AgentNode capabilities (standalone=False)
    child_agent_full = FractalAgentNode(
        node_id="projected-child-full",
        dispatcher=dispatcher,
        provider=provider,
        parent=root_agent,
        standalone=False, # Use full AgentNode
        context_projection=projection
    )

    # Verify Projection Applied (Sync Add to Memory)
    # Projection items are added to memory during init
    print("🔍 Verifying projected context in child memory...")

    # Check Plan (Projected as L1/L2 usually? context_projection adds them to memory via _apply_projection)
    # AgentNode._apply_projection -> self.memory.add_sync(unit)

    # Projection converts relevant_facts to memories
    # The parent plan is usually converted to a Context or Plan type unit

    units = child_agent_full.memory.get_statistics()
    print(f"   Memory Stats: {units}")

    # Check if "Module X handles payments" is in child's memory
    found_fact = False
    # Only check L4/L3/L2/L1 - _apply_projection usually puts them in L2 or L3 depending on implementation
    # Let's check all
    all_units = await child_agent_full.memory.query(MemoryQuery())
    for u in all_units:
        if "Module X handles payments" in str(u.content):
            found_fact = True
            break

    assert found_fact
    print("✅ Projection Fact found in Child Memory")

if __name__ == "__main__":
    asyncio.run(test_hot_plug_lifecycle(infrastructure()))
    asyncio.run(test_memory_sharing_and_isolation(infrastructure()))
    asyncio.run(test_context_projection_init(infrastructure()))
