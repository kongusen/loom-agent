import pytest
from loom.execution.agent import Agent
from loom.core.message import AssistantMessage

# Re-use mocks from test_engine in a real implementation we might put them in conftest.py
from tests.unit.execution.test_engine import MockLLM, MockTool

@pytest.mark.asyncio
async def test_agent_runnable_interface():
    """Verify Agent implements Runnable interface correctly."""
    
    response_msg = AssistantMessage(content="Hello World")
    llm = MockLLM(responses=[response_msg])
    
    agent = Agent(name="TestAgent", llm=llm)
    
    # Test invoke with string
    result = await agent.invoke("Hi")
    assert result.content == "Hello World"
    
    # Test invoke with Message
    # Reset LLM
    llm.call_count = 0
    from loom.core.message import UserMessage
    result2 = await agent.invoke(UserMessage(content="Hi"))
    assert result2.content == "Hello World"
