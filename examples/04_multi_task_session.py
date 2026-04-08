"""04 - Multi-Run Session."""

import asyncio

from loom import AgentConfig, ModelRef, RunContext, SessionConfig, create_agent
from loom.runtime import RunState


async def main():
    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="You are a thoughtful API design assistant.",
        )
    )
    session = agent.session(SessionConfig(id="multi-run-demo"))

    goals = [
        "List three key features of a good API",
        "Explain why context management matters in LLM agents",
        "Summarize the two previous answers in one sentence",
    ]

    results = []
    for goal in goals:
        context = RunContext(inputs={"previous_results": results}) if results else None
        result = await session.run(goal, context=context)
        results.append(result.output)
        status = "✓" if result.state == RunState.COMPLETED else "✗"
        print(f"{status} {goal[:50]}")
        print(f"  → {result.output}\n")

    print(f"Session runs: {len(session.list_runs())}")


asyncio.run(main())
