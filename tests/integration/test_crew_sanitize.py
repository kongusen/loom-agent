import pytest
import asyncio
from loom.node.crew import CrewNode
from loom.node.agent import AgentNode
from loom.api.main import LoomApp
from loom.builtin.memory.sanitizers import BubbleUpSanitizer

class MockSanitizer(BubbleUpSanitizer):
    async def sanitize(self, context: str, target_token_limit: int) -> str:
        return f"SANITIZED: {context}"

@pytest.mark.asyncio
async def test_crew_sanitization():
    app = LoomApp()
    
    # Create dummy agents
    agent1 = AgentNode(node_id="a1", dispatcher=app.dispatcher)
    # We mock agent process to return huge text
    async def mock_process(event):
        return {"response": "A very long result from Agent 1 that needs cleaning."}
    agent1.process = mock_process # Monkey patch for simple unit test
    
    # Create Crew with Mock Sanitizer
    sanitizer = MockSanitizer()
    crew = CrewNode(
        node_id="crew", 
        dispatcher=app.dispatcher, 
        agents=[agent1],
        sanitizer=sanitizer
    )
    
    # Allow subscriptions to settle
    await asyncio.sleep(0.1)
    
    # Execute
    result = await app.run("Task", target="node/crew")
    
    # Result from app.run depends on what CrewNode returns in process()
    # CrewNode._execute_sequential returns {"final_output": ..., "trace": ...}
    
    # Wait, app.run currently returns event.data["result"].
    # CrewNode.process calls _execute_sequential.
    
    assert isinstance(result, dict)
    trace = result["trace"]
    assert len(trace) == 1
    assert trace[0]["sanitized"] == "SANITIZED: A very long result from Agent 1 that needs cleaning."
