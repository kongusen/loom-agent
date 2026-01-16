"""
LoomMemory Demonstration Script
"""

import asyncio
from typing import Any

# Mock infrastructure
from loom.kernel.core import Dispatcher, UniversalEventBus
from loom.memory.config import ContextConfig
from loom.memory.types import MemoryQuery, MemoryTier, MemoryType, MemoryUnit
from loom.node.agent import AgentNode
from loom.protocol.cloudevents import CloudEvent


class MockProvider:
    """Mock LLM Provider for demo."""

    async def chat(self, messages: list[dict[str, str]], **_kwargs) -> Any:
        print(f"\n🤖 [LLM Input Context]: {len(messages)} messages")
        for msg in messages:
            content = str(msg.get("content", ""))[:50] + "..."
            print(f"  - {msg['role']}: {content}")

        # Simulate intelligent behavior
        # Check user intent
        user_msg = next((m for m in messages if m["role"] == "user"), None)
        user_content = str(user_msg["content"]) if user_msg else ""

        if "Analyze" in user_content:
            # Check if we have already loaded the context (look for tool output)
            has_loaded = any(m["role"] == "tool" for m in messages)

            if has_loaded:
                return {"content": "Data loaded. The revenue is $5M. Analysis complete."}

            return {
                "content": "I see some resources available. Let me check the Q3 Report.",
                "tool_calls": [{"name": "load_context", "arguments": {"resource_id": "FACT-001"}}],
            }
        elif "loaded" in user_content:
            return {"content": "Data loaded. The revenue is $5M. Analysis complete."}

        return {"content": "I am ready."}


async def main():
    print("🚀 Starting LoomMemory Demo...\n")

    # 1. Setup
    dispatcher = Dispatcher(bus=UniversalEventBus())
    provider = MockProvider()

    # Configure Context Strategy
    config = ContextConfig(strategy="snippets")
    config.curation_config.use_snippets = True

    agent = AgentNode(
        node_id="demo-agent",
        dispatcher=dispatcher,
        provider=provider,  # NOTE: provider arg name changed in my refactor if not careful?
        # Checking my previous write_to_file...
        # __init__(..., provider: Optional[LLMProvider] = None, ...)
        # Yes, it is 'provider' in AgentNode, was 'llm_provider' in V2.
        context_config=config,
    )

    # 2. Plant a "Long-term Fact" in L4 Memory
    print("💾 Seeding L4 Memory with a Fact...")
    fact_id = "FACT-001"
    agent.memory.add(
        MemoryUnit(
            id=fact_id,
            content="Q3 Financial Report: Revenue $5M, Growth 20%.",
            tier=MemoryTier.L4_GLOBAL,
            type=MemoryType.FACT,
            importance=0.9,
            metadata={"name": "Q3 Report", "full_available": True},
        )
    )

    # 3. Verify Snippet Generation
    # We manually trigger curation to see what the agent SHOULD see
    print("🔍 Verifying Snippets (Static Check)...")
    strategies = agent.assembler.strategy
    curated = strategies.curate(agent.memory, config.curation_config, task_context="Analyze Q3")
    snippet = next((u for u in curated if u.metadata.get("snippet_of") == fact_id), None)

    if snippet:
        print(f"✅ Fact transformed into snippet: {snippet.content}")
    else:
        print("❌ Fact not found in snippets!")

    # 4. Run Agent Loop
    print("\n🎬 Running Agent Process...")
    result = await agent.process(
        CloudEvent.create(
            source="/user", type="node.request", data={"content": "Analyze the Q3 Report please."}
        )
    )

    print(f"\n🏁 Agent Final Output: {result}")

    # 5. Verify Context After Load
    l2_facts = agent.memory.query(MemoryQuery(tiers=[MemoryTier.L2_WORKING]))
    loaded = [u for u in l2_facts if u.metadata.get("loaded_from") == fact_id]

    if loaded:
        print(f"✅ Loaded Resource into L2: {loaded[0].content}")
    else:
        print("❌ Resource NOT loaded into L2")


if __name__ == "__main__":
    asyncio.run(main())
