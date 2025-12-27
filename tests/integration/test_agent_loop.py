import pytest
import asyncio
from typing import List, Any
from loom.node.agent import AgentNode
from loom.node.tool import ToolNode
from loom.api.main import LoomApp
from loom.protocol.cloudevents import CloudEvent
from loom.interfaces.llm import LLMProvider, LLMResponse, StreamChunk
from loom.protocol.mcp import MCPToolDefinition as ToolDefinition

class MockSequenceLLM(LLMProvider):
    def __init__(self, responses: List[LLMResponse]):
         self.responses = responses
         self.calls = 0
         self.stream_calls = 0

    async def chat(self, messages: List[Any], tools: List[Any] = None, config: Any = None) -> LLMResponse:
        if self.calls < len(self.responses):
            resp = self.responses[self.calls]
            self.calls += 1
            return resp
        return LLMResponse(content="Limit reached")

    async def stream_chat(self, *args, **kwargs):
        # Use the sequence responses in streaming mode too
        if self.stream_calls < len(self.responses):
            resp = self.responses[self.stream_calls]

            # If response has tool calls, don't increment and cause fallback
            # The agent will fall back to non-streaming mode
            if resp.tool_calls:
                # Don't increment stream_calls - let chat() handle it
                return
                # This will cause the stream to be empty, triggering fallback

            self.stream_calls += 1

            # If response has content, stream it
            if resp.content:
                words = resp.content.split()
                for word in words:
                    yield StreamChunk(type="text", content=word + " ", metadata={})

            yield StreamChunk(type="done", content="", metadata={})
        else:
            yield StreamChunk(type="text", content="Limit reached", metadata={})
            yield StreamChunk(type="done", content="", metadata={})

class MockTool(ToolNode):
    async def process(self, event: CloudEvent) -> Any:
        return {"result": "Tool success"}

@pytest.mark.asyncio
async def test_agent_react_loop():
    app = LoomApp()
    
    # Define tool
    tool_def = ToolDefinition(name="test_tool", description="test tool", inputSchema={})
    tool = MockTool(node_id="tool", dispatcher=app.dispatcher, tool_def=tool_def, func=lambda x: "success")

    
    # Mock LLM sequence
    # 1. Call tool
    resp1 = LLMResponse(content="", tool_calls=[{"name": "test_tool", "arguments": {}}])
    # 2. Final answer
    resp2 = LLMResponse(content="Final Answer")
    
    provider = MockSequenceLLM([resp1, resp2])
    
    agent = AgentNode(
        node_id="agent", 
        dispatcher=app.dispatcher, 
        tools=[tool], 
        provider=provider
    )
    
    # Run
    # app.run uses target="node/agent"
    # We must ensure agent knows about the tool node? 
    # AgentNode init: known_tools={name: tool}. 
    # Yes, we passed tools=[tool].
    
    # Allow logic to settle?
    await asyncio.sleep(0.5)
    
    # Need to subscribe tool to "node.request/tool" if not already?
    # ToolNode.__init__ subscribes to its id.
    # AgentNode calls subject=target_tool.source_uri (which is based on node_id).
    
    result = await app.run("Do task", target="node/agent")
    
    assert result["response"] == "Final Answer"
    assert result["iterations"] == 2
    assert provider.calls == 2

@pytest.mark.asyncio
async def test_max_iterations():
    app = LoomApp()
    
    # Mock infinite tool loops
    resp_loop = LLMResponse(content="", tool_calls=[{"name": "test_tool", "arguments": {}}])

    # Infinite provider
    class InfiniteLLM(LLMProvider):
        async def chat(self, *args, **kwargs):
            return resp_loop
        async def stream_chat(self, *args, **kwargs):
            # Return empty stream to trigger fallback to chat()
            # This avoids infinite loop while still testing max_iterations
            return
            yield  # Make it a generator
            
    tool_def = ToolDefinition(name="test_tool", description="test", inputSchema={})
    tool = MockTool(node_id="tool", dispatcher=app.dispatcher, tool_def=tool_def, func=lambda x: "success")
    
    provider = InfiniteLLM()
    
    agent = AgentNode(
        node_id="agent_loop", 
        dispatcher=app.dispatcher, 
        tools=[tool], 
        provider=provider
    )
    
    await asyncio.sleep(0.1)
    
    # Run with limited iterations
    # How to pass max_iterations via app.run?
    # app.run(task="...", max_iterations=2) -> not supported in signature yet.
    # app.run creates event with data={"task": ...}
    # We can rely on default for now (5) or add param.
    
    # Let's bypass app.run for precise control or trust default 5.
    event = CloudEvent.create(
        source="user",
        type="node.request",
        data={"task": "Loop", "max_iterations": 3},
        subject="node/agent_loop"
    )
    
    result = await agent.process(event)
    
    assert "Error: Maximum iterations reached" in result["response"]
    assert result["iterations"] == 3
