# LLM Provider Integrations

Loom uses the `LLMProvider` protocol to support any language model.

## OpenAI
The most common integration. Use the `openai` Python library.

```python
import os
from loom.interfaces.llm import LLMProvider, LLMResponse
from openai import AsyncOpenAI

class OpenAIProvider(LLMProvider):
    def __init__(self, model="gpt-4-turbo"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = model

    async def chat(self, messages, tools=None) -> LLMResponse:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools or None
        )
        msg = response.choices[0].message
        tool_calls = [t.model_dump() for t in msg.tool_calls] if msg.tool_calls else []
        return LLMResponse(content=msg.content, tool_calls=tool_calls)
```

## Anthropic
Anthropic's Claude models require handling different tool call formats.

```python
from anthropic import AsyncAnthropic

class AnthropicProvider(LLMProvider):
    def __init__(self, model="claude-3-opus-20240229"):
        self.client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = model

    async def chat(self, messages, tools=None) -> LLMResponse:
        # Convert tools to Anthropic format
        anthropic_tools = self._convert_tools(tools)
        
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=messages,
            tools=anthropic_tools
        )
        # Parse response to standard LLMResponse...
```
