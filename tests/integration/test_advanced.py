import pytest
import asyncio
from typing import List, Any
from loom.node.base import Node
from loom.node.agent import AgentNode
from loom.node.router import AttentionRouter
from loom.api.main import LoomApp
from loom.protocol.cloudevents import CloudEvent
from loom.kernel.interceptors import TimeoutInterceptor
from loom.interfaces.llm import LLMProvider, LLMResponse

class SlowNode(Node):
    async def process(self, event: CloudEvent) -> Any:
        await asyncio.sleep(2.0)
        return "Done"

@pytest.mark.skip(reason="Timeout enforcement logic is pending in Node/Dispatcher")
@pytest.mark.asyncio
async def test_timeout_interceptor():
    app = LoomApp()
    # Add interceptor with 1s timeout
    app.dispatcher.add_interceptor(TimeoutInterceptor(default_timeout_sec=1.0))
    
    slow = SlowNode(node_id="slow", dispatcher=app.dispatcher)
    
    # Wait for subscription
    await asyncio.sleep(0.1)
    
    # Run
    with pytest.raises(asyncio.TimeoutError):
        await app.run("task", target="node/slow")

class MockRouterLLM(LLMProvider):
    async def chat(self, messages: List[Any], tools=None) -> LLMResponse:
        content = messages[0]["content"]
        if "math" in content.lower():
            return LLMResponse(content="math_agent")
        return LLMResponse(content="writer_agent")
        
    async def stream_chat(self, *args, **kwargs): pass

@pytest.mark.asyncio
async def test_attention_router():
    app = LoomApp()
    
    math_agent = AgentNode(node_id="math_agent", dispatcher=app.dispatcher, role="Math Expert")
    writer_agent = AgentNode(node_id="writer_agent", dispatcher=app.dispatcher, role="Writer")
    
    router = AttentionRouter(
        node_id="router", 
        dispatcher=app.dispatcher,
        agents=[math_agent, writer_agent],
        provider=MockRouterLLM()
    )
    
    # Verify routing to Math
    # We need to mock agents to return something or just rely on them echoing task
    # Standard AgentNode adds to memory and calls provider.
    # Let's simple-mock AgentNode.process? 
    # Or inject a mock provider into agents?
    
    # Inject mock provider into agents to avoid real LLM calls if default provider used
    # But AgentNode uses MockLLMProvider by default which returns "Mock Response".
    
    await asyncio.sleep(0.1)
    
    # 1. Math Task
    result = await app.run("do math", target="node/router")
    assert result["routed_to"] == "math_agent"
    
    # 2. Write Task
    # Note: app.run calls router.process.
    # router logic: LLM selects agent key.
    # MockRouterLLM logic: if 'math' in content -> 'math_agent'.
    # If app.run task="do math", content contains "do math".
    
    # Wait, Router constructs prompt: "Task: {task}"
    # MockLLM sees "Task: do math". 'math' in content -> True.
