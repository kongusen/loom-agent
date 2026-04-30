"""Runtime component wiring for mutable AgentEngine fields."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runtime.engine import AgentEngine


class RuntimeWiring:
    """Refresh extracted runtime components from AgentEngine facade fields."""

    def __init__(self, engine: AgentEngine) -> None:
        self.engine = engine

    def refresh(self) -> None:
        """Mirror mutable engine fields into all runtime components."""
        self.refresh_signal_runtime()
        self.refresh_tool_runtime()
        self.refresh_memory_runtime()
        self.refresh_context_runtime()
        self.refresh_provider_runtime()
        self.refresh_run_lifecycle()
        self.refresh_loop_services()

    def refresh_signal_runtime(self) -> None:
        self.engine.signal_runtime.context_manager = self.engine.context_manager

    def refresh_tool_runtime(self) -> None:
        tool_runtime = self.engine.tool_runtime
        tool_runtime.context_manager = self.engine.context_manager
        tool_runtime.hook_manager = self.engine.hook_manager
        tool_runtime.tool_registry = self.engine.tool_registry
        tool_runtime.tool_executor = self.engine.tool_executor
        tool_runtime.governance_policy = self.engine.governance_policy
        tool_runtime.tool_governance = self.engine.tool_governance
        tool_runtime.permission_manager = self.engine.permission_manager
        tool_runtime.veto_authority = self.engine.veto_authority

    def refresh_memory_runtime(self) -> None:
        memory_runtime = self.engine.memory_runtime
        memory_runtime.context_manager = self.engine.context_manager
        memory_runtime.memory_store = self.engine.memory_store
        memory_runtime.memory_providers = self.engine.memory_providers
        memory_runtime.semantic_memory = self.engine.semantic_memory

    def refresh_context_runtime(self) -> None:
        context_runtime = self.engine.context_runtime
        context_runtime.context_manager = self.engine.context_manager
        context_runtime.ecosystem_manager = self.engine.ecosystem_manager
        context_runtime.skill_injection_policy = self.engine.skill_injection_policy

    def refresh_provider_runtime(self) -> None:
        provider_runtime = self.engine.provider_runtime
        provider_runtime.provider = self.engine.provider
        provider_runtime.config = self.engine.config
        provider_runtime.context_manager = self.engine.context_manager

    def refresh_run_lifecycle(self) -> None:
        run_lifecycle = self.engine.run_lifecycle
        run_lifecycle.config = self.engine.config
        run_lifecycle.context_manager = self.engine.context_manager
        run_lifecycle.context_runtime = self.engine.context_runtime
        run_lifecycle.ecosystem_manager = self.engine.ecosystem_manager
        run_lifecycle.heartbeat = self.engine.heartbeat
        run_lifecycle.memory_runtime = self.engine.memory_runtime

    def refresh_loop_services(self) -> None:
        services = self.engine.loop_runner.services
        services.context_manager = self.engine.context_manager
        services.memory_runtime = self.engine.memory_runtime
