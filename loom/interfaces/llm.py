"""
LLM Provider Interface
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncIterator, Optional, Literal
from pydantic import BaseModel

class LLMResponse(BaseModel):
    """
    Standardized response from an LLM.
    """
    content: str
    tool_calls: List[Dict[str, Any]] = []
    token_usage: Optional[Dict[str, int]] = None


class StreamChunk(BaseModel):
    """
    Structured chunk for streaming LLM output.

    Enables real-time injection of thoughts into the stream (System 2 → System 1).
    """
    type: Literal["text", "tool_call", "thought_injection", "done"]
    content: str | dict
    metadata: Dict[str, Any] = {}


from loom.protocol.interfaces import LLMProviderProtocol

class LLMProvider(LLMProviderProtocol, ABC):
    """
    Abstract Interface for LLM Backends (OpenAI, Anthropic, Local).
    """

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """
        Generate a response for a given chat history.
        """
        pass

    @abstractmethod
    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream the response as structured chunks.

        UPGRADED: Now returns StreamChunk instead of raw strings,
        enabling real-time thought injection and tool call support.
        """
        pass
