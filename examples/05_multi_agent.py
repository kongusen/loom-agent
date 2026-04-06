"""05 - Multi-Agent Orchestration

Use TaskPlanner to decompose a goal into dependent subtasks,
then execute them in dependency order via the Coordinator.

The Coordinator + TaskPlanner pattern is Loom's answer to CrewAI crews
and AutoGen conversations — but with explicit dependency graphs and
timeout/error handling built in.

Run:
    python examples/05_multi_agent.py
"""

import asyncio
from loom.orchestration import TaskPlanner, Coordinator, EventBus, Task


class SimpleAgent:
    """Minimal agent stub — replace with a real LLM-backed agent."""

    def __init__(self, depth: int = 0):
        self.depth = depth
        self.feedback: list[dict] = []

    async def run(self, goal: str) -> str:
        return f"[agent@depth={self.depth}] completed: {goal}"


class SimpleSubAgentManager:
    """Minimal SubAgentManager that spawns SimpleAgent instances."""

    def __init__(self, max_depth: int = 3):
        self.max_depth = max_depth

    async def spawn(self, goal: str, depth: int = 0, inherit_context: bool = True):
        from loom.types import SubAgentResult
        if depth >= self.max_depth:
            return SubAgentResult(success=False, output="", depth=depth, error="MAX_DEPTH_EXCEEDED")
        agent = SimpleAgent(depth=depth + 1)
        output = await agent.run(goal)
        return SubAgentResult(success=True, output=output, depth=depth + 1)


async def main():
    # 1. Plan: decompose a goal into sequential subtasks
    planner = TaskPlanner()
    tasks = planner.create_plan(
        "Research Loom framework; Write a summary; Review the summary",
        max_tasks=3,
    )
    print("=== Plan ===")
    for t in tasks:
        deps = t.dependencies or ["(none)"]
        print(f"  {t.id}: {t.goal[:50]}  deps={deps}")

    # 2. Coordinate: execute plan with timeout + error handling
    bus = EventBus()
    coordinator = Coordinator(event_bus=bus)
    manager = SimpleSubAgentManager()
    coordinator.register_agent("main", manager)

    print("\n=== Execution ===")
    results = await coordinator.execute_plan("main", planner, depth=0)

    summary = coordinator.aggregate_results(results)
    print(f"  Total tasks : {summary['total']}")
    print(f"  Succeeded   : {summary['succeeded']}")
    print(f"  Failed      : {summary['failed']}")
    for tid, output in summary["outputs"].items():
        print(f"  {tid}: {output}")


asyncio.run(main())
