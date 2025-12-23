# Building Agents

Agents are the decision-makers in Loom.

## Basic Agent
The simplest agent requires a `dispatcher`, `node_id`, and `role`.

```python
from loom.node.agent import AgentNode

agent = AgentNode(
    node_id="agent/basic",
    dispatcher=app.dispatcher,
    role="Generic Assistant"
)
```

## Customizing Behavior

### System Prompt
Define the personality and constraints.

```python
agent = AgentNode(
    ...,
    system_prompt="You are a sarcastic coding assistant. Only answer in Python code."
)
```

### Adding Tools
Give the agent capabilities.

```python
agent = AgentNode(
    ...,
    tools=[calculator_tool, search_tool]
)
```

### Custom LLM Provider
By default, Loom uses a `MockLLMProvider` for testing. To use a real LLM (e.g., OpenAI), implement the `LLMProvider` protocol.

```python
from typing import List, Dict, Any, AsyncIterator
from loom.interfaces.llm import LLMProvider, LLMResponse
import openai

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model
    
    async def chat(self, messages: List[Dict[str, Any]], tools=None) -> LLMResponse:
        # Convert tools to OpenAI format if necessary
        # This is a simplified example
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools
        )
        msg = response.choices[0].message
        return LLMResponse(
            content=msg.content,
            tool_calls=[tc.model_dump() for tc in msg.tool_calls] if msg.tool_calls else []
        )
        
    async def stream_chat(self, *args, **kwargs) -> AsyncIterator[str]:
        # Implement streaming logic
        yield "..."

agent = AgentNode(
    ...,
    provider=OpenAIProvider(api_key="sk-...")
)
```
