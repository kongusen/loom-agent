"""02 - Provider Configuration

Connect a real LLM provider (Anthropic, OpenAI, or Gemini).
Reads API key from environment variable.

Run:
    ANTHROPIC_API_KEY=sk-ant-... python examples/02_provider_config.py
    OPENAI_API_KEY=sk-...       python examples/02_provider_config.py
"""

import asyncio
import os
from loom.api import AgentRuntime, AgentProfile, AgentConfig, LLMConfig


def build_provider():
    if key := os.getenv("ANTHROPIC_API_KEY"):
        from loom.providers import AnthropicProvider
        return AnthropicProvider(api_key=key)
    if key := os.getenv("OPENAI_API_KEY"):
        from loom.providers import OpenAIProvider
        return OpenAIProvider(api_key=key, base_url=os.getenv("OPENAI_BASE_URL"))
    if key := os.getenv("GEMINI_API_KEY"):
        from loom.providers import GeminiProvider
        return GeminiProvider(api_key=key)
    return None  # falls back to local summary


async def main():
    provider = build_provider()
    profile = AgentProfile(
        id="demo",
        name="Demo Agent",
        config=AgentConfig(
            name="demo",
            llm=LLMConfig(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), max_tokens=256),
            system_prompt="You are a concise technical assistant.",
        ),
    )
    runtime = AgentRuntime(profile=profile, provider=provider)
    session = runtime.create_session()

    task = session.create_task("What makes Loom different from LangChain?")
    result = await task.start().wait()

    print(f"Provider: {type(provider).__name__ if provider else 'local fallback'}")
    print(f"Output:   {result.summary}")


asyncio.run(main())
