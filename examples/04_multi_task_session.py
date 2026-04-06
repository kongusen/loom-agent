"""04 - Multi-Task Session

Run multiple tasks in a single session, passing context between them.

Run:
    python examples/04_multi_task_session.py
"""

import asyncio
from loom.api import AgentRuntime, AgentProfile, RunState


async def main():
    runtime = AgentRuntime(profile=AgentProfile.from_preset("default"))
    session = runtime.create_session()

    goals = [
        "List three key features of a good API",
        "Explain why context management matters in LLM agents",
        "Summarize the two previous answers in one sentence",
    ]

    results = []
    for goal in goals:
        context = {"previous_results": results} if results else {}
        task = session.create_task(goal, context=context)
        result = await task.start().wait()
        results.append(result.summary)
        status = "✓" if result.state == RunState.COMPLETED else "✗"
        print(f"{status} {goal[:50]}")
        print(f"  → {result.summary}\n")

    print(f"Session tasks: {len(session.list_tasks())}")


asyncio.run(main())
