
import asyncio
from loom.kernel.core import UniversalEventBus
from loom.kernel.core import Dispatcher
from loom.node.agent import AgentNode
from loom.protocol.cloudevents import CloudEvent

class MockLLMProvider:
    async def chat(self, messages, **kwargs):
        # Simulate LLM response
        last_msg = messages[-1]["content"]
        if "marketing" in last_msg.lower():
             return {"content": "Here is a detailed strategy...", "tool_calls": []}
        return {"content": "4", "tool_calls": []}

async def main():
    print("🚀 Starting System 1/2 Architecture Demo...\n")
    
    # Setup
    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)
    
    # Create Agent with Custom Configuration
    # We add a rule that "magic" is a complex System 2 task
    from loom.config.cognitive import CognitiveConfig
    from loom.config.router import RouterRule

    custom_config = CognitiveConfig.default()
    custom_config.router_rules.append(RouterRule(
        name="magic_is_complex",
        keywords=["magic"],
        target_system="SYSTEM_2"
    ))

    agent = AgentNode(
        node_id="sys_agent_01",
        dispatcher=dispatcher,
        provider=MockLLMProvider(),
        cognitive_config=custom_config
    )
    
    # Scenario 1: Simple Fact (System 1)
    print("\n--- Scenario 1: Simple Query ---")
    query1 = "What is 2 + 2?"
    print(f"User: {query1}")
    
    # Manually trigger process for demo
    event1 = CloudEvent(
        type="node.request",
        source="user",
        subject="sys_agent_01",
        data={"content": query1}
    )
    
    result1 = await agent.process(event1)
    print(f"Agent ({result1.get('system')}): {result1.get('response')}")

    # Scenario 2: Custom Rule Test (System 2)
    print("\n--- Scenario 2: Custom Config Rule (Magic -> S2) ---")
    query2 = "Tell me a magic trick." # "magic" should trigger S2
    print(f"User: {query2}")
    
    event2 = CloudEvent(
        type="node.request",
        source="user",
        subject="sys_agent_01",
        data={"content": query2}
    )
    
    result2 = await agent.process(event2)
    print(f"Agent Output (Should be S2/Complex): {result2}")
    
    print("\n✅ Demo Complete.")

if __name__ == "__main__":
    asyncio.run(main())
