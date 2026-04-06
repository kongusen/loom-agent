"""Basic agent example"""

import asyncio
from loom import Agent
from loom.providers import AnthropicProvider


async def main():
    # Create provider
    provider = AnthropicProvider(api_key="your-api-key")
    
    # Create agent
    agent = Agent(provider)
    
    # Run agent
    result = await agent.run("Solve a simple task", max_steps=10)
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
