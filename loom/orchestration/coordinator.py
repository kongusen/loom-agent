"""Agent coordinator"""

import asyncio
from typing import Any

from ..runtime.delegation import DelegationRequest, DelegationResult
from ..types import CoordinationEvent, SubAgentResult
from .events import CoordinationEventBus
from .planner import TaskPlanner


class Coordinator:
    """Coordinate multiple agents"""

    def __init__(self, event_bus: CoordinationEventBus):
        self.event_bus = event_bus
        self.agents: dict[str, Any] = {}

    def register_agent(self, agent_id: str, manager: Any):
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
        task_timeout: float = 120.0,
    ) -> dict[str, SubAgentResult]:
        """Execute ready tasks for one registered agent manager."""
        manager = self.agents.get(agent_id)
        if manager is None:
            raise KeyError(f"Agent '{agent_id}' is not registered")
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
                request = DelegationRequest(
                    goal=task.goal,
                    depth=depth,
                    inherit_context=inherit_context,
                    timeout=task_timeout,
                    metadata={"task_id": task.id, "agent_id": agent_id},
                )
                try:
                    result = (await self._delegate(manager, request)).to_subagent_result()
                except TimeoutError:
                    result = SubAgentResult(success=False, output="", depth=depth, error="timeout")
                except Exception as exc:
                    result = SubAgentResult(success=False, output="", depth=depth, error=str(exc))
                planner.update_status(task.id, "completed" if result.success else "failed")
                self._publish(
                    "task.completed" if result.success else "task.failed",
                    agent_id,
                    task,
                    result=result,
                )
                return task.id, result

            pairs = await asyncio.gather(*[_run_task(t) for t in pending])
            results.update(dict(pairs))

        return results

    async def _delegate(self, manager: Any, request: DelegationRequest) -> DelegationResult:
        delegate = getattr(manager, "delegate", None)
        if callable(delegate):
            coro = delegate(request)
            if request.timeout is not None:
                raw_result = await asyncio.wait_for(coro, timeout=request.timeout)
            else:
                raw_result = await coro
            if isinstance(raw_result, DelegationResult):
                return raw_result
            if isinstance(raw_result, SubAgentResult):
                return DelegationResult.from_subagent_result(raw_result)
            return DelegationResult(
                success=True,
                output=getattr(raw_result, "output", raw_result),
                depth=request.depth + 1,
            )

        spawn = getattr(manager, "spawn", None)
        if not callable(spawn):
            raise TypeError("Registered agent manager must provide delegate() or spawn()")

        coro = spawn(
            request.goal,
            depth=request.depth,
            inherit_context=request.inherit_context,
        )
        if request.timeout is not None:
            result = await asyncio.wait_for(coro, timeout=request.timeout)
        else:
            result = await coro
        if isinstance(result, DelegationResult):
            return result
        return DelegationResult.from_subagent_result(result)

    def aggregate_results(self, results: dict[str, SubAgentResult]) -> dict:
        """Aggregate sub-agent outputs into a structured summary."""
        succeeded = {tid: r for tid, r in results.items() if r.success}
        failed = {tid: r for tid, r in results.items() if not r.success}
        return {
            "total": len(results),
            "succeeded": len(succeeded),
            "failed": len(failed),
            "outputs": {tid: r.output for tid, r in succeeded.items()},
            "errors": {tid: r.error or "unknown" for tid, r in failed.items()},
        }

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
            CoordinationEvent(
                id=f"{topic}:{task.id}",
                sender=agent_id,
                topic=topic,
                payload=payload,
                delta_h=0.5,
                priority="medium",
            )
        )
