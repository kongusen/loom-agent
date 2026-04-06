"""Agent coordinator"""

import asyncio
from .events import EventBus
from .planner import TaskPlanner
from .subagent import SubAgentManager
from ..types import Event, SubAgentResult


class Coordinator:
    """Coordinate multiple agents"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.agents: dict[str, SubAgentManager] = {}
    
    def register_agent(self, agent_id: str, manager: SubAgentManager):
        """Register an agent"""
        self.agents[agent_id] = manager
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent"""
        self.agents.pop(agent_id, None)

    async def execute_plan(
        self,
        agent_id: str,
        planner: TaskPlanner,
        depth: int = 0,
        inherit_context: bool = True,
    ) -> dict[str, SubAgentResult]:
        """Execute ready tasks for one registered agent manager."""
        manager = self.agents[agent_id]
        results: dict[str, SubAgentResult] = {}

        while True:
            ready_tasks = planner.get_ready_tasks()
            pending = [task for task in ready_tasks if task.id not in results]
            if not pending:
                break

            for task in pending:
                planner.update_status(task.id, "running")
                self._publish("task.started", agent_id, task)

            async def _run_task(task):
                result = await manager.spawn(task.goal, depth=depth, inherit_context=inherit_context)
                planner.update_status(task.id, "completed" if result.success else "failed")
                self._publish("task.completed" if result.success else "task.failed", agent_id, task, result=result)
                return task.id, result

            pairs = await asyncio.gather(*[_run_task(t) for t in pending])
            results.update(dict(pairs))

        return results

    def aggregate_results(self, results: dict[str, SubAgentResult]) -> str:
        """Aggregate sub-agent outputs into one summary string."""
        ordered = []
        for task_id, result in results.items():
            status = "ok" if result.success else "error"
            ordered.append(f"[{task_id}:{status}] {result.output}")
        return "\n".join(ordered)

    def _publish(
        self,
        topic: str,
        agent_id: str,
        task,
        result: SubAgentResult | None = None,
    ) -> None:
        """Publish a coordination event."""
        payload = {"task_id": task.id, "goal": task.goal, "status": task.status}
        if result is not None:
            payload["result"] = result.output
            payload["success"] = result.success

        self.event_bus.publish(
            Event(
                id=f"{topic}:{task.id}",
                sender=agent_id,
                topic=topic,
                payload=payload,
                delta_h=0.5,
                priority="medium",
            )
        )
