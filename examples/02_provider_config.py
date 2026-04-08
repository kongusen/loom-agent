"""02 - Provider Configuration.

The public Agent API uses explicit ModelRef objects plus environment variables.
"""

import asyncio
import os

from loom import AgentConfig, GenerationConfig, ModelRef, create_agent


async def main():
    provider = os.getenv("LOOM_PROVIDER", "anthropic").lower()
    model_name = os.getenv("LOOM_MODEL_NAME", "claude-sonnet-4")
    if provider == "openai":
        model = ModelRef.openai(model_name)
    elif provider == "gemini":
        model = ModelRef.gemini(model_name)
    elif provider == "ollama":
        model = ModelRef.ollama(model_name)
    elif provider == "qwen":
        model = ModelRef.qwen(model_name)
    else:
        model = ModelRef.anthropic(model_name)

    agent = create_agent(
        AgentConfig(
            model=model,
            instructions="You are a concise technical assistant.",
            generation=GenerationConfig(max_output_tokens=256),
        )
    )
    result = await agent.run("What makes Loom different from LangChain?")

    print(f"Model:   {model.identifier}")
    print(f"Output:  {result.output}")


asyncio.run(main())
