"""01 - Hello Agent.

Minimal Loom usage with the public Agent API.
No API key required; Loom falls back to a local summary when no provider is available.
"""

import asyncio

from loom import AgentConfig, ModelRef, create_agent


async def main():
    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="You are a concise technical assistant.",
        )
    )
    result = await agent.run("Summarize the Loom framework in one sentence")
    print(f"State:  {result.state.value}")
    print(f"Output: {result.output}")


asyncio.run(main())
