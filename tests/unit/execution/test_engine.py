import pytest
import asyncio
from typing import List, Optional, Dict, Any, AsyncGenerator

from loom.core.message import Message, UserMessage, AssistantMessage, ToolCall, ToolMessage, FunctionCall
from loom.core.runnable import RunnableConfig
from loom.execution.engine import RecursiveEngine
from loom.builtin.llms.base import BaseLLM
from loom.builtin.tools.base import BaseTool

# --- Mocks ---

class MockLLM(BaseLLM):
    """Mock LLM that returns pre-configured responses."""
    def __init__(self, responses: List[AssistantMessage]):
        self.responses = responses
        self.call_count = 0
        self.model_name = "mock"

    async def invoke(self, input: List[Message], config=None, tools=None, **kwargs) -> AssistantMessage:
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response
        return AssistantMessage(content="No more mock responses")

    async def stream(self, *args, **kwargs) -> AsyncGenerator[str, None]:
        yield "Mock stream"

class MockTool(BaseTool):
    """Mock tool that echoes input."""
    def __init__(self, name="mock_tool"):
        self.name = name
        self.description = "Mock Tool"
        # Dummy schema
        from pydantic import BaseModel
        class Schema(BaseModel):
            arg: str
        self.args_schema = Schema

    async def invoke(self, input: Dict[str, Any], config=None, **kwargs) -> str:
        return f"Executed {self.name} with {input}"

# --- Tests ---

@pytest.mark.asyncio
async def test_simple_think_act_loop():
    """Verify standard Think -> Act -> Observe loop."""
    
    # Setup
    # Round 1: Assistant calls tool
    tool_call = ToolCall(
        id="call_1", 
        function=FunctionCall(name="mock_tool", arguments='{"arg": "test"}')
    )
    msg1 = AssistantMessage(content="Thinking...", tool_calls=[tool_call])
    
    # Round 2: Assistant observes result and answers
    msg2 = AssistantMessage(content="Done: Executed mock_tool with {'arg': 'test'}")
    
    llm = MockLLM(responses=[msg1, msg2])
    tool = MockTool()
    
    engine = RecursiveEngine(llm=llm, tools=[tool])
    
    # Run
    input_msg = UserMessage(content="Run tool")
    result = await engine.run(input_msg)
    
    # Verify
    assert result.content == msg2.content
    assert llm.call_count == 2
    # Verify State (indirectly via LLM responses)
    # The engine should have added tool result to history between calls

@pytest.mark.asyncio
async def test_max_depth_limit():
    """Verify recursion stops at max depth."""
    
    # LLM keeps returning tool calls forever
    infinite_tool_call = ToolCall(id="call_x", function=FunctionCall(name="mock_tool", arguments='{"arg": "x"}'))
    msg = AssistantMessage(content="Infinite...", tool_calls=[infinite_tool_call])
    
    # Infinite supply of responses
    class InfiniteLLM(BaseLLM):
        model_name="infinite"
        async def invoke(self, *args, **kwargs):
            return msg
        async def stream(self, *args, **kwargs): yield ""

    llm = InfiniteLLM()
    tool = MockTool()
    
    # Set max_depth low
    engine = RecursiveEngine(llm=llm, tools=[tool], max_depth=3)
    
    # Run should raise RecursionError
    with pytest.raises(RecursionError):
        await engine.run(UserMessage(content="Start"))
