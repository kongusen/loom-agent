"""Task planner — LLM-based decomposition and DAG execution."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Awaitable

from ..types import SubTask, TaskAd, TaskResult, LLMProvider, CompletionParams, UserMessage, SystemMessage

logger = logging.getLogger(__name__)

DECOMPOSE_PROMPT = """Decompose this task into independent subtasks. Return JSON array:
[{{"id": "a", "description": "...", "domain": "...", "dependencies": [], "estimated_complexity": 0.3}}]
Keep subtasks to 5 or fewer. Task: {task}"""


class TaskPlanner:
    """Decompose tasks into DAG of subtasks, execute respecting dependencies."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def decompose(self, task: TaskAd) -> list[SubTask]:
        result = await self._provider.complete(CompletionParams(
            messages=[
                SystemMessage(content="You are a task planner. Return only valid JSON."),
                UserMessage(content=DECOMPOSE_PROMPT.format(task=task.description)),
            ],
            max_tokens=1024, temperature=0.3,
        ))
        try:
            raw = json.loads(result.content)
            return [SubTask(**s) for s in raw[:5]]
        except (json.JSONDecodeError, TypeError):
            return [SubTask(description=task.description, domain=task.domain,
                            estimated_complexity=task.estimated_complexity)]

    async def aggregate(self, task: TaskAd, results: list[TaskResult]) -> str:
        summary = "\n---\n".join(f"[{r.task_id}] {r.content}" for r in results)
        result = await self._provider.complete(CompletionParams(
            messages=[
                SystemMessage(content="Synthesize the sub-task results into a coherent final answer."),
                UserMessage(content=f"Original task: {task.description}\n\nResults:\n{summary}"),
            ],
            max_tokens=2048, temperature=0.3,
        ))
        return result.content

    async def execute_dag(
        self,
        subtasks: list[SubTask],
        executor: Callable[[SubTask], Awaitable[str]],
    ) -> list[TaskResult]:
        results: list[TaskResult] = []
        done: set[str] = set()

        # Cycle detection: if no progress in a round, break
        while len(done) < len(subtasks):
            ready = [s for s in subtasks if s.id not in done
                     and all(d in done for d in s.dependencies)]
            if not ready:
                # Remaining tasks have unresolvable deps → cycle
                for s in subtasks:
                    if s.id not in done:
                        results.append(TaskResult(task_id=s.id, agent_id="", content="Error: cyclic dependency", success=False))
                break
            tasks = [executor(s) for s in ready]
            outputs = await asyncio.gather(*tasks, return_exceptions=True)
            for s, out in zip(ready, outputs):
                if isinstance(out, Exception):
                    results.append(TaskResult(task_id=s.id, agent_id="", content=f"Error: {out}", success=False))
                else:
                    results.append(TaskResult(task_id=s.id, agent_id="", content=str(out), success=True))
                done.add(s.id)
        return results
