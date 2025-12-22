from typing import Any, AsyncGenerator, Dict, List, Optional
import os

from loom.builtin.llms.base import BaseLLM
from loom.core.message import Message, AssistantMessage, ToolCall
from loom.core.runnable import RunnableConfig
from loom.interfaces.llm import LLMEvent

try:
    from anthropic import AsyncAnthropic
    from anthropic.types import Message as AnthropicMessage
except ImportError:
    AsyncAnthropic = None # type: ignore

class AnthropicLLM(BaseLLM):
    """
    Adapter for Anthropic's Claude models.
    Requires `anthropic` package: pip install anthropic
    """

    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        timeout: float = 120.0,
        max_retries: int = 2,
        **kwargs: Any
    ):
        if AsyncAnthropic is None:
            raise ImportError("Anthropic package not installed. Install with: pip install anthropic")
            
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API Key must be provided or set in ANTHROPIC_API_KEY env var.")
            
        self.client = AsyncAnthropic(
            api_key=self.api_key,
            max_retries=max_retries,
            timeout=timeout
        )
        self.model_name = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.kwargs = kwargs

    async def invoke(
        self,
        input: List[Message],
        config: Optional[RunnableConfig] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any
    ) -> AssistantMessage:
        
        system_prompt = self._extract_system_prompt(input)
        response = await self.client.messages.create(
            model=self.model_name,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=self._convert_messages(input),
            # tools=tools, # Pending: Anthropic tool format conversion
            **{**self.kwargs, **kwargs}
        )
        
        content = response.content[0].text
        # Note: Tool handling for Anthropic requires block parsing, simplifying for now
        return AssistantMessage(content=content)

    async def stream(
        self,
        input: List[Message],
        config: Optional[RunnableConfig] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any
    ) -> AsyncGenerator[LLMEvent, None]:
        
        system_prompt = self._extract_system_prompt(input)
        async with self.client.messages.stream(
            model=self.model_name,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=self._convert_messages(input),
            **{**self.kwargs, **kwargs}
        ) as stream:
             async for text in stream.text_stream:
                 yield {
                     "delta": text,
                     "finish_reason": None,
                     "usage": None
                 }
                 
    def _extract_system_prompt(self, messages: List[Message]) -> str:
        return next((m.content for m in messages if m.role == "system"), "")

    def _convert_messages(self, messages: List[Message]) -> List[Dict]:
        # Anthropic doesn't support 'system' role in messages list, it's a separate arg
        return [
            {"role": m.role, "content": m.content} 
            for m in messages 
            if m.role in ["user", "assistant"]
        ]

class ClaudeLLM(AnthropicLLM):
    """Alias for AnthropicLLM"""
    pass
