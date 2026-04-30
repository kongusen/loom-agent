"""Run lifecycle coordination shared by batch and streaming execution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class PreparedRun:
    """Normalized run setup shared by all execution modes."""

    goal: str
    instructions: str
    context: dict[str, Any] | None
    session_id: str | None


class RunLifecycleRuntime:
    """Owns run preparation, successful finalization, and heartbeat cleanup."""

    def __init__(
        self,
        *,
        config: Any,
        context_manager: Any,
        context_runtime: Any,
        ecosystem_manager: Any,
        heartbeat: Any,
        memory_runtime: Any,
        memory_enabled: Callable[[], bool],
        drain_signals: Callable[[], Any],
        heartbeat_handler: Callable[[dict[str, Any], str], Any],
    ) -> None:
        self.config = config
        self.context_manager = context_manager
        self.context_runtime = context_runtime
        self.ecosystem_manager = ecosystem_manager
        self.heartbeat = heartbeat
        self.memory_runtime = memory_runtime
        self.memory_enabled = memory_enabled
        self.drain_signals = drain_signals
        self.heartbeat_handler = heartbeat_handler

    def prepare(
        self,
        *,
        goal: str,
        instructions: str,
        context: dict[str, Any] | None,
        session_id: str | None,
        history: list[dict[str, Any]] | None,
    ) -> PreparedRun:
        instructions = self._merge_system_prompt_additions(instructions)

        self.context_manager.current_goal = goal
        self.context_runtime.initialize_context(goal, instructions, context)
        self.context_runtime.inject_session_history(history)
        self.drain_signals()

        if session_id and self.memory_enabled():
            self.memory_runtime.load_session_memory(session_id)

        if self.memory_runtime.semantic_memory is not None:
            self.memory_runtime.inject_semantic_memories(goal)
        self.memory_runtime.inject_provider_memories(goal, session_id)

        if self.heartbeat:
            self.heartbeat.start(self.heartbeat_handler)

        return PreparedRun(
            goal=goal,
            instructions=instructions,
            context=context,
            session_id=session_id,
        )

    def finalize_success(self, prepared: PreparedRun, output: str) -> None:
        if prepared.session_id and self.memory_enabled():
            self.memory_runtime.save_session_memory(prepared.session_id)
        self.memory_runtime.sync_memory_providers(prepared.goal, output, prepared.session_id)

    def stop(self) -> None:
        if self.heartbeat:
            self.heartbeat.stop()

    def _merge_system_prompt_additions(self, instructions: str) -> str:
        if self.ecosystem_manager:
            mcp_additions = self.ecosystem_manager.get_system_prompt_additions()
            if mcp_additions:
                instructions = (
                    f"{instructions}\n\n{mcp_additions}".strip() if instructions else mcp_additions
                )
        provider_prompt = self.memory_runtime.provider_system_prompt()
        if provider_prompt:
            instructions = f"{instructions}\n\n{provider_prompt}".strip()
        return instructions
