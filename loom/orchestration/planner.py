"""Task planner"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Task:
    """Task definition"""

    id: str
    goal: str
    dependencies: list[str]
    status: str = "pending"


class TaskPlanner:
    """Plan and schedule tasks"""

    def __init__(self):
        self.tasks: dict[str, Task] = {}
        self._task_counter = 0

    def add_task(self, task: Task):
        """Add a task"""
        self.tasks[task.id] = task

    async def plan(self, goal: str, provider: Any = None, max_tasks: int = 5) -> list[Task]:
        """Create a plan using LLM if available, else heuristic fallback."""
        if provider is not None:
            try:
                return await self._llm_plan(goal, provider, max_tasks)
            except Exception:
                pass
        return self.create_plan(goal, max_tasks)

    async def _llm_plan(self, goal: str, provider: Any, max_tasks: int) -> list[Task]:
        """Ask LLM to decompose goal into numbered steps."""
        from ..providers.base import CompletionParams, CompletionRequest

        params = CompletionParams(max_tokens=512, temperature=0.3)
        messages = [
            {
                "role": "system",
                "content": "Decompose the goal into at most "
                f"{max_tasks} concrete sequential steps. Output one step per line, "
                "numbered 1. 2. 3. No extra text.",
            },
            {"role": "user", "content": goal},
        ]
        response = await provider.complete_request(CompletionRequest.create(messages, params))
        steps = []
        for line in response.content.splitlines():
            line = line.strip().lstrip("0123456789.-) ").strip()
            if line:
                steps.append(line)
        steps = steps[:max_tasks] or [goal]
        return self._build_chain(steps)

    def create_plan(self, goal: str, max_tasks: int = 5) -> list[Task]:
        """Create a simple sequential task plan from a goal string."""
        steps = self._split_goal(goal)[:max_tasks]
        if not steps:
            steps = [goal.strip() or "Complete task"]
        return self._build_chain(steps)

    def _build_chain(self, steps: list[str]) -> list[Task]:
        """Build a sequential dependency chain from steps."""
        planned: list[Task] = []
        previous_id: str | None = None
        for step in steps:
            self._task_counter += 1
            task_id = f"task_{self._task_counter}"
            task = Task(id=task_id, goal=step, dependencies=[previous_id] if previous_id else [])
            self.add_task(task)
            planned.append(task)
            previous_id = task_id
        return planned

    def get_task(self, task_id: str) -> Task | None:
        return self.tasks.get(task_id)

    def update_status(self, task_id: str, status: str) -> Task:
        task = self.tasks[task_id]
        task.status = status
        return task

    def all_completed(self) -> bool:
        return bool(self.tasks) and all(task.status == "completed" for task in self.tasks.values())

    def get_ready_tasks(self) -> list[Task]:
        ready = []
        for task in self.tasks.values():
            if task.status == "pending":
                deps_done = all(
                    self.tasks[dep].status == "completed"
                    for dep in task.dependencies
                    if dep in self.tasks
                )
                if deps_done:
                    ready.append(task)
        return ready

    def _split_goal(self, goal: str) -> list[str]:
        normalized = goal.replace("->", "\n").replace(" and then ", "\n")
        raw_parts = []
        for line in normalized.splitlines():
            for part in line.split(";"):
                raw_parts.extend(part.split(","))
        return [part.strip(" -") for part in raw_parts if part.strip(" -")]
