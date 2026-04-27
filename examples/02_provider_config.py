"""02 - Provider Configuration.

The public Agent API uses explicit Model objects plus environment variables.
"""

import asyncio
import os

from loom import Agent, Generation, Model


async def main():
    provider = os.getenv("LOOM_PROVIDER", "anthropic").lower()
    model_name = os.getenv("LOOM_MODEL_NAME", "claude-sonnet-4")
    if provider == "openai":
        model = Model.openai(model_name)
    elif provider == "gemini":
        model = Model.gemini(model_name)
    elif provider == "ollama":
        model = Model.ollama(model_name)
    elif provider == "qwen":
        model = Model.qwen(model_name)
    else:
        model = Model.anthropic(model_name)

    agent = Agent(
        model=model,
        instructions="You are a concise technical assistant.",
        generation=Generation(max_output_tokens=256),
    )
    result = await agent.run("What makes Loom different from LangChain?")

    print(f"Model:   {model.identifier}")
    print(f"Output:  {result.output}")


asyncio.run(main())
