"""13 - Repo Copilot.

End-to-end application-style demo for a repository copilot.
Works with the public `Agent -> Session` API.
"""

import asyncio
import os

from loom import Agent, Model, RunContext, SessionConfig, tool
from loom.config import PolicyConfig, PolicyContext, ToolAccessPolicy, ToolPolicy


@tool(description="Read repository files", read_only=True)
async def read_file(path: str) -> str:
    samples = {
        "README.md": "# Loom\nBuild stateful agents with one public Agent API.",
        "loom/config.py": "class Runtime: ...\nclass Capability: ...",
        "wiki/09-cookbook/README.md": "Application Cookbook for real Loom app patterns.",
    }
    return samples.get(path, f"No sample content for {path}")


def resolve_model():
    provider = os.getenv("LOOM_PROVIDER", "openai" if os.getenv("OPENAI_API_KEY") else "anthropic").lower()
    model_name = os.getenv("LOOM_MODEL_NAME")
    if provider == "openai":
        return Model.openai(
            model_name or os.getenv("OPENAI_MODEL") or "gpt-4.1",
            api_base=os.getenv("OPENAI_BASE_URL"),
            api_key_env="OPENAI_API_KEY",
        )
    if provider == "gemini":
        return Model.gemini(model_name or "gemini-2.5-pro")
    if provider == "qwen":
        return Model.qwen(model_name or "qwen-max")
    if provider == "ollama":
        return Model.ollama(model_name or "llama3", api_base=os.getenv("OLLAMA_BASE_URL"))
    return Model.anthropic(model_name or "claude-sonnet-4")


async def main():
    agent = Agent(
        model=resolve_model(),
        instructions=(
            "You are a repository copilot. "
            "Prefer concrete, code-aware answers and keep recommendations scoped."
        ),
        tools=[read_file],
        policy=PolicyConfig(
            tools=ToolPolicy(
                access=ToolAccessPolicy(
                    allow=["read_file"],
                    read_only_only=True,
                )
            ),
            context=PolicyContext.named("repo"),
        ),
    )

    session = agent.session(
        SessionConfig(
            id="repo-copilot-demo",
            metadata={"repo": "loom-agent"},
        )
    )

    first = await session.run("Summarize what this repository is trying to expose to application developers.")
    second = await session.run(
        "Based on the previous answer, what should be tightened next?",
        context=RunContext(
            inputs={
                "repo": "loom-agent",
                "previous_answer": first.output,
                "focus": "public API clarity",
            }
        ),
    )

    print("=== Repo Copilot ===")
    print(f"First:  {first.output}")
    print(f"Second: {second.output}")
    print(f"Runs:   {len(session.list_runs())}")


asyncio.run(main())
