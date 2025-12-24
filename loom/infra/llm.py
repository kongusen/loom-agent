"""
Mock LLM Provider for Testing
"""

from typing import List, Dict, Any, AsyncIterator, Optional
from loom.interfaces.llm import LLMProvider, LLMResponse

class MockLLMProvider(LLMProvider):
    """
    A Mock Provider that returns canned responses.
    Useful for unit testing and demos without API keys.
    """
    
    async def chat(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        last_msg = messages[-1]["content"].lower()
        
        # Simple keywords
        if "search" in last_msg:
            # Simulate Tool Call
            query = last_msg.replace("search", "").strip() or "fractal"
            return LLMResponse(
                content="",
                tool_calls=[{
                    "name": "search",
                    "arguments": {"query": query},
                    "id": "call_mock_123"
                }]
            )
            
        return LLMResponse(content=f"Mock response to: {last_msg}")

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncIterator[str]:
        yield "Mock "
        yield "stream "
        yield "response."
