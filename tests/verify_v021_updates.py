
import asyncio
import time
from typing import Any, Dict, List, Optional
from loom.core.runnable import Runnable, RunnableConfig
from loom.core.message import Message, UserMessage, AssistantMessage, ToolCall, ToolMessage
from loom.execution.agent import Agent
from loom.execution.engine import RecursiveEngine
from loom.patterns.composition import Group, Sequence
from loom.builtin.tools.base import BaseTool

# --- Mocks ---

from loom.builtin.llms.base import BaseLLM

class MockTool(BaseTool):
    def __init__(self, name: str, sleep_time: float = 0.0):
        self.name = name
        self.sleep_time = sleep_time
        self.description = "Mock tool"
        self.args_schema = type("Args", (), {"model_json_schema": lambda: {}})
        
    async def invoke(self, input: Dict[str, Any], config: Optional[RunnableConfig] = None, **kwargs) -> str:
        if self.sleep_time > 0:
            await asyncio.sleep(self.sleep_time)
        return f"{self.name} result: {input}"
        
    def get_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Mock tool",
                "parameters": {"type": "object", "properties": {}}
            }
        }

class MockLLM(BaseLLM):
    model_name: str = "mock-model"
    
    async def invoke(self, input: List[Message], config: Optional[RunnableConfig] = None, tools: Optional[List[Dict]] = None, **kwargs) -> AssistantMessage:
        # Check if we should simulate tool calls
        last_msg = input[-1]
        text = last_msg.get_text_content() if hasattr(last_msg, 'get_text_content') else str(last_msg.content)
        
        if "call tools" in text:
            return AssistantMessage(
                content="Calling tools...",
                tool_calls=[
                    ToolCall(id="1", type="function", function={"name":"tool1", "arguments": "{}"}),
                    ToolCall(id="2", type="function", function={"name":"tool1", "arguments": "{}"}),
                    ToolCall(id="3", type="function", function={"name":"tool1", "arguments": "{}"})
                ]
            )
        return AssistantMessage(content=f"Echo: {text}")

    async def stream(self, input: List[Message], config: Optional[RunnableConfig] = None, tools: Optional[List[Dict]] = None, **kwargs):
        yield await self.invoke(input, config, tools, **kwargs)


class Aggregator(Runnable[Dict[str, Any], str]):
    async def invoke(self, input: Dict[str, Any], config: Optional[RunnableConfig] = None, **kwargs) -> str:
        vals = []
        for v in input.values():
            if hasattr(v, 'content'):
                vals.append(v.content)
            else:
                vals.append(str(v))
        return f"Aggregated: {vals}"

# --- Tests ---

async def test_streaming():
    print("\n--- Test 1: Streaming ---")
    agent = Agent(name="TestBot", llm=MockLLM())
    
    # Since Agent inherits Runnable(ABC), it should have a default stream method
    # that yields the result of invoke()
    chunks = []
    async for chunk in agent.stream("Hello Stream"):
        chunks.append(chunk)
        print(f"Received chunk: {chunk}")
        
    assert len(chunks) == 1
    assert chunks[0].content == "Echo: Hello Stream"
    print("✅ Streaming passed (default implementation)")

async def test_concurrency():
    print("\n--- Test 2: Concurrency ---")
    # Setup: 3 tool calls, each takes 0.5s.
    # Max concurrency = 1 -> Total time ~1.5s
    # Max concurrency = 3 -> Total time ~0.5s
    
    slow_tool = MockTool("tool1", sleep_time=0.5)
    agent = Agent(name="SlowBot", llm=MockLLM(), tools=[slow_tool])
    
    # Case A: Sequence (Concurrency=1)
    start = time.perf_counter()
    msg = UserMessage(content="call tools")
    config = RunnableConfig(max_concurrency=1)
    await agent.invoke(msg, config=config)
    duration_seq = time.perf_counter() - start
    print(f"Sequential duration: {duration_seq:.2f}s (Expected ~1.5s)")
    
    # Case B: Parallel (Concurrency=3)
    start = time.perf_counter()
    config = RunnableConfig(max_concurrency=3)
    await agent.invoke(msg, config=config)
    duration_par = time.perf_counter() - start
    print(f"Parallel duration: {duration_par:.2f}s (Expected ~0.5s)")
    
    assert duration_seq > 1.2
    assert duration_par < 0.8
    print("✅ Concurrency passed")

async def test_group_aggregator():
    print("\n--- Test 3: Group Aggregator ---")
    
    r1 = MockLLM()
    r2 = MockLLM()
    
    group = Group(
        steps={"a": r1, "b": r2},
        aggregator=Aggregator()
    )
    
    # Input needs to be compatible with MockLLM (List[Message] or string converted by Agent, but here MockLLM takes List[Message])
    # However, Group passes input to all steps.
    # MockLLM expects List[Message].
    msg = UserMessage(content="Group Test")
    
    # We invoke with [msg], MockLLM receives [msg]
    result = await group.invoke([msg])
    print(f"Group Result: {result}")
    
    assert "Aggregated" in result
    assert "Echo: Group Test" in result
    print("✅ Group Aggregator passed")

async def main():
    try:
        await test_streaming()
        await test_concurrency()
        await test_group_aggregator()
        print("\n🎉 All Verification Tests Passed!")
    except Exception as e:
        print(f"\n❌ Verification Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
