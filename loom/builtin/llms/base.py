from typing import List, Dict, Any, Optional, AsyncGenerator
from abc import ABC, abstractmethod
from loom.core.runnable import Runnable, RunnableConfig
from loom.core.message import Message, AssistantMessage

class BaseLLM(Runnable[List[Message], AssistantMessage]):
    """
    Abstract Base Class for LLMs.

    Philosophy:
    - LLM is also a Runnable (can be composed directly)
    - Input: List[Message]
    - Output: AssistantMessage
    """

    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None

    @abstractmethod
    async def invoke(
        self,
        input: List[Message],
        config: Optional[RunnableConfig] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AssistantMessage:
        """
        Synchronous-semantic execution. (Underlying implementation might be streaming, but exposed as one-shot)

        Args:
            input: List of messages.
            config: Runtime configuration.
            tools: Tool definitions (OpenAI format).

        Returns:
            AssistantMessage
        """
        ...

    @abstractmethod
    async def stream(
        self,
        input: List[Message],
        config: Optional[RunnableConfig] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Streaming execution (returns text chunks).

        Yields:
            Text content chunks.
        """
        ...
