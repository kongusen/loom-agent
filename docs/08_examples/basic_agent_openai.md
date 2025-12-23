# Basic Agent with OpenAI

This example demonstrates how to build a real Loom agent using `openai`.

## Prerequisites
```bash
pip install loom-agent openai
export OPENAI_API_KEY="sk-..."
```

## `example.py`

```python
import asyncio
import os
from typing import List, Dict, Any, AsyncIterator
from loom.api.main import LoomApp
from loom.node.agent import AgentNode
from loom.interfaces.llm import LLMProvider, LLMResponse
import openai

# 1. Implement Real OpenAI Provider
class OpenAIProvider(LLMProvider):
    def __init__(self, model="gpt-4"):
        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    async def chat(self, messages: List[Dict[str, Any]], tools=None) -> LLMResponse:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools
        )
        msg = response.choices[0].message
        return LLMResponse(
            content=msg.content,
            tool_calls=[t.model_dump() for t in msg.tool_calls] if msg.tool_calls else []
        )
        
    async def stream_chat(self, *args, **kwargs) -> AsyncIterator[str]:
        # Simple non-streaming fallback for example
        yield ""

async def main():
    # 2. Init App
    app = LoomApp()
    
    # 3. Create Agent
    agent = AgentNode(
        node_id="gpt-agent",
        dispatcher=app.dispatcher,
        role="Helpful Assistant",
        provider=OpenAIProvider()
    )
    app.add_node(agent)
    
    # 4. Run
    print("User: Hello, who are you?")
    response = await app.run("Hello, who are you?", "gpt-agent")
    print(f"Agent: {response['response']}")

if __name__ == "__main__":
    asyncio.run(main())
```
