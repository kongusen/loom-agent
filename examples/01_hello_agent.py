"""01 - Hello Agent

Minimal Loom usage: create a runtime, session, task, and run.
No API key required — uses local fallback execution.

Run:
    python examples/01_hello_agent.py
"""

import asyncio
from loom.api import AgentRuntime, AgentProfile


async def main():
    runtime = AgentRuntime(profile=AgentProfile.from_preset("default"))
    session = runtime.create_session()

    task = session.create_task("Summarize the Loom framework in one sentence")
    run = task.start()

    result = await run.wait()
    print(f"State:  {result.state.value}")
    print(f"Output: {result.summary}")


asyncio.run(main())
