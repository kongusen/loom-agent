"""03 - Events and Artifacts

Subscribe to the event stream and inspect artifacts produced by a run.

Run:
    python examples/03_events_and_artifacts.py
"""

import asyncio
from loom.api import AgentRuntime, AgentProfile


async def main():
    runtime = AgentRuntime(profile=AgentProfile.from_preset("default"))
    session = runtime.create_session()
    task = session.create_task("Analyze the structure of a Python project")
    run = task.start()

    result = await run.wait()

    # Events
    print("=== Events ===")
    async for event in run.events():
        print(f"  [{event.type}] {event.payload}")

    # Artifacts
    print("\n=== Artifacts ===")
    for artifact in await run.artifacts():
        print(f"  {artifact.kind}: {artifact.title} → {artifact.uri}")

    print(f"\nDuration: {result.duration_ms}ms")


asyncio.run(main())
