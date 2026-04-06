"""Runtime handles for Loom framework

Handles provide controlled operation interfaces with lifecycle management
"""

from datetime import datetime
from typing import Optional, AsyncIterator
from .models import (
    Session,
    Task,
    Run,
    Event,
    Approval,
    Artifact,
    RunState,
    RunResult,
)
from .events import EventStream
from ..providers.base import CompletionParams


class SessionHandle:
    """Session handle - controlled session operations"""

    def __init__(self, session: Session, runtime: "AgentRuntime"):
        self.session = session
        self.runtime = runtime
        self._tasks: dict[str, Task] = session._tasks

    @property
    def id(self) -> str:
        return self.session.id

    def create_task(
        self,
        goal: str,
        context: Optional[dict] = None
    ) -> "TaskHandle":
        """Create a task"""
        task = Task(
            session_id=self.session.id,
            goal=goal,
            context=context or {}
        )
        self._tasks[task.id] = task
        return TaskHandle(task, self)

    def get_task(self, task_id: str) -> Optional["TaskHandle"]:
        """Get task by ID"""
        task = self._tasks.get(task_id)
        return TaskHandle(task, self) if task else None

    def list_tasks(self) -> list["TaskHandle"]:
        """List all tasks"""
        return [TaskHandle(task, self) for task in self._tasks.values()]

    async def close(self) -> None:
        """Close session"""
        self.session._closed = True
        self._tasks.clear()


class TaskHandle:
    """Task handle - controlled task operations"""

    def __init__(self, task: Task, session: SessionHandle):
        self.task = task
        self.session = session
        self._runs: dict[str, Run] = task._runs

    @property
    def id(self) -> str:
        return self.task.id

    @property
    def goal(self) -> str:
        return self.task.goal

    def start(self) -> "RunHandle":
        """Start a new run"""
        run = Run(
            task_id=self.task.id,
            goal=self.task.goal,
            state=RunState.QUEUED
        )
        self._runs[run.id] = run
        return RunHandle(run, self)

    def get_run(self, run_id: str) -> Optional["RunHandle"]:
        """Get run by ID"""
        run = self._runs.get(run_id)
        return RunHandle(run, self) if run else None

    def list_runs(self) -> list["RunHandle"]:
        """List all runs"""
        return [RunHandle(run, self) for run in self._runs.values()]


class RunHandle:
    """Run handle - core runtime interface"""

    def __init__(self, run: Run, task: TaskHandle):
        self.run = run
        self.task = task
        self._events: list[Event] = run._events
        self._artifacts: list[Artifact] = run._artifacts
        self._approvals: dict[str, Approval] = run._approvals

    @property
    def id(self) -> str:
        return self.run.id

    @property
    def state(self) -> RunState:
        return self.run.state

    async def wait(self) -> RunResult:
        """Wait for run completion"""
        if self.run.state in {
            RunState.COMPLETED,
            RunState.FAILED,
            RunState.CANCELLED,
            RunState.BLOCKED_BY_CAPABILITY,
            RunState.BLOCKED_BY_POLICY,
        }:
            return self._build_result()

        self.run.state = RunState.RUNNING
        self.run.updated_at = datetime.now()

        await self._publish_event(
            "run.started",
            {"goal": self.run.goal, "task_id": self.task.id},
        )

        try:
            summary = await self._execute_run()
            self.run.current_step += 1
            self.run.summary = summary
            self.run.state = RunState.COMPLETED
            self.run.updated_at = datetime.now()

            artifact = Artifact(
                run_id=self.run.id,
                kind="text",
                title="Run Summary",
                uri=f"run://{self.run.id}/summary",
                metadata={"content": summary, "task_id": self.task.id},
            )
            self._store_artifact(artifact)

            await self._publish_event(
                "run.completed",
                {"summary": summary, "artifact_id": artifact.artifact_id},
            )
            return self._build_result()
        except Exception as exc:
            self.run.state = RunState.FAILED
            self.run.updated_at = datetime.now()

            await self._publish_event(
                "run.failed",
                {"error": str(exc)},
                visibility="audit",
            )

            return self._build_result(error={"message": str(exc)})

    async def events(self) -> AsyncIterator[Event]:
        """Subscribe to event stream"""
        runtime = self.task.session.runtime
        if self.run.state in {
            RunState.COMPLETED,
            RunState.FAILED,
            RunState.CANCELLED,
            RunState.BLOCKED_BY_CAPABILITY,
            RunState.BLOCKED_BY_POLICY,
        }:
            for event in runtime.event_bus.list_by_run(self.run.id):
                yield event
            return

        stream = EventStream(runtime.event_bus, self.run.id, preload_history=True)
        async for event in stream:
            yield event

    async def approve(self, approval_id: str, decision: str = "approve") -> None:
        """Submit approval decision"""
        if approval_id not in self._approvals:
            raise ValueError(f"Approval {approval_id} not found")
        
        approval = self._approvals[approval_id]
        if approval.status != "pending":
            raise ValueError(f"Approval {approval_id} already resolved")
        
        approval.status = "approved" if decision == "approve" else "rejected"
        
        # Resume run if approved
        if approval.status == "approved" and self.run.state == RunState.WAITING_APPROVAL:
            self.run.state = RunState.RUNNING

    async def pause(self) -> None:
        """Pause execution"""
        if self.run.state not in [RunState.RUNNING, RunState.QUEUED]:
            raise ValueError(f"Cannot pause from state {self.run.state.value}")
        
        self.run.state = RunState.PAUSED

    async def resume(self) -> None:
        """Resume execution"""
        if self.run.state != RunState.PAUSED:
            raise ValueError(f"Cannot resume from state {self.run.state.value}")
        self.run.state = RunState.RUNNING
        await self.wait()

    async def cancel(self) -> None:
        """Cancel execution"""
        if self.run.state in [RunState.COMPLETED, RunState.FAILED, RunState.CANCELLED]:
            raise ValueError(f"Cannot cancel from state {self.run.state.value}")
        
        self.run.state = RunState.CANCELLED

    async def artifacts(self) -> list[Artifact]:
        """Get artifacts"""
        stored = self.task.session.runtime.artifact_store.list_by_run(self.run.id)
        return stored or self._artifacts.copy()

    async def transcript(self) -> dict:
        """Get transcript"""
        return {
            "run_id": self.run.id,
            "task_id": self.task.id,
            "state": self.run.state.value,
            "summary": self.run.summary,
            "events": [e.__dict__ for e in self._events],
            "artifacts": [a.__dict__ for a in self._artifacts]
        }

    async def _execute_run(self) -> str:
        """Execute via Agent (full L* loop) or minimal fallback."""
        runtime = self.task.session.runtime
        provider = runtime.provider
        if provider is None:
            return self._local_summary()

        try:
            from ..agent.core import Agent
            from ..config import AgentConfig
            config = AgentConfig(
                system_prompt=runtime.profile.config.system_prompt,
                model=runtime.profile.config.llm.model,
                max_tokens=runtime.profile.config.llm.max_tokens or 4096,
                temperature=runtime.profile.config.llm.temperature,
            )
            agent = Agent(provider=provider, config=config)
            done = await agent.run(self._user_prompt())
            return done.content or self._local_summary()
        except Exception:
            # Fallback to minimal single-turn completion
            params = CompletionParams(
                model=runtime.profile.config.llm.model,
                max_tokens=runtime.profile.config.llm.max_tokens or 512,
                temperature=runtime.profile.config.llm.temperature,
            )
            response = await provider.complete(self._build_messages(), params)
            return response.strip() or self._local_summary()

    def _build_messages(self) -> list[dict[str, str]]:
        """Build minimal prompt messages for provider-backed execution."""
        messages: list[dict[str, str]] = []
        system_prompt = self.task.session.runtime.profile.config.system_prompt.strip()
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": self._user_prompt()})
        return messages

    def _user_prompt(self) -> str:
        """Render the task goal and context into one prompt."""
        prompt = f"Goal: {self.run.goal}"
        if self.task.task.context:
            prompt += f"\nContext: {self.task.task.context}"
        return prompt

    def _local_summary(self) -> str:
        """Fallback execution summary when no provider is configured."""
        if self.task.task.context:
            return f"Completed goal: {self.run.goal} with context keys {sorted(self.task.task.context.keys())}"
        return f"Completed goal: {self.run.goal}"

    async def _publish_event(
        self,
        event_type: str,
        payload: dict,
        visibility: str = "user",
    ) -> None:
        """Append and publish a run event."""
        event = Event(
            run_id=self.run.id,
            type=event_type,
            visibility=visibility,
            payload=payload,
        )
        self._events.append(event)
        await self.task.session.runtime.event_bus.publish(event)

    def _store_artifact(self, artifact: Artifact) -> None:
        """Append and persist an artifact."""
        self._artifacts.append(artifact)
        self.task.session.runtime.artifact_store.store(artifact)

    def _build_result(self, error: dict | None = None) -> RunResult:
        """Materialize the current run state into a result object."""
        duration_ms = int(
            max(
                0.0,
                (self.run.updated_at - self.run.created_at).total_seconds(),
            )
            * 1000
        )
        return RunResult(
            run_id=self.run.id,
            state=self.run.state,
            summary=self.run.summary,
            artifacts=self._artifacts.copy(),
            events=self._events.copy(),
            error=error,
            duration_ms=duration_ms,
        )
