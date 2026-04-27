"""03 - Events and Artifacts."""

import asyncio

from loom import Agent, Model, SessionConfig


async def main():
    agent = Agent(
        model=Model.anthropic("claude-sonnet-4"),
        instructions="You are a repository analyst.",
    )
    run = agent.session(SessionConfig(id="events-demo")).start(
        "Analyze the structure of a Python project"
    )

    # Events
    print("=== Events ===")
    async for event in run.events():
        print(f"  [{event.type}] {event.payload}")

    result = await run.wait()

    # Artifacts
    print("\n=== Artifacts ===")
    for artifact in await run.artifacts():
        print(f"  {artifact.kind}: {artifact.title} → {artifact.uri}")

    print(f"\nDuration: {result.duration_ms}ms")


asyncio.run(main())
