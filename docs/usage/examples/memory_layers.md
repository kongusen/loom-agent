# Configuring Memory Layers (L1-L4)

This example demonstrates how to configure the Loom memory system with specific retention policies and semantic search capabilities.

```python
import asyncio
from loom.agent import Agent
from loom.config.memory import MemoryConfig, MemoryLayerConfig
from loom.providers.llm import OpenAIProvider
from loom.memory.vector_store import InMemoryVectorStore

async def main():
    # 1. Setup LLM provider
    llm = OpenAIProvider(api_key="sk-mock", model="gpt-4")

    # 2. Define Memory Configuration
    # L1: Very short term (1 hour), highly active (auto-included)
    # L4: Permanent knowledge, large capacity
    memory_config = MemoryConfig(
        l1=MemoryLayerConfig(
            capacity=20,
            retention_hours=1,
            auto_compress=True
        ),
        l2=MemoryLayerConfig(
            capacity=100,
            retention_hours=24
        ),
        l3=MemoryLayerConfig(
            capacity=1000,
            retention_hours=24 * 7 # 1 week
        ),
        l4=MemoryLayerConfig(
            capacity=10000,
            retention_hours=None, # Infinite
            promote_threshold=10  # Harder to get into L4
        )
    )

    # 3. Create Agent with Memory
    agent = Agent.from_llm(
        llm=llm,
        node_id="memory-agent",
        system_prompt="You maintain a vast archive of knowledge.",
        memory_config=memory_config
    )

    print(f"Agent {agent.node_id} created with 4-layer memory.")

if __name__ == "__main__":
    asyncio.run(main())
```

## How Promotion Works
- Items start in **L1**.
- If accessed frequently (e.g., >3 times), they move to **L2**.
- **L4** supports vector search if you configure an embedding provider.
