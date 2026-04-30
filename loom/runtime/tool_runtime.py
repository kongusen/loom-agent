"""Tool coordination runtime extracted from AgentEngine internals."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..providers.base import ProviderToolParameter, ProviderToolSpec
from ..safety.hooks import AgentContext, HookDecision
from ..types import ToolCall, ToolResult


class ToolRuntime:
    """Owns tool parsing, governance sync, and execution pipeline."""

    def __init__(
        self,
        *,
        emit: Callable[..., None],
        current_iteration: Callable[[], int],
        context_manager: Any,
        hook_manager: Any,
        tool_registry: Any,
        tool_executor: Any,
        governance_policy: Any,
        tool_governance: Any,
        permission_manager: Any,
        veto_authority: Any,
    ) -> None:
        self.emit = emit
        self.current_iteration = current_iteration
        self.context_manager = context_manager
        self.hook_manager = hook_manager
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor
        self.governance_policy = governance_policy
        self.tool_governance = tool_governance
        self.permission_manager = permission_manager
        self.veto_authority = veto_authority

    def parse_tool_calls(self, response: dict[str, Any]) -> list[ToolCall]:
        tool_calls = response.get("tool_calls", [])
        return [call for call in tool_calls if isinstance(call, ToolCall)]

    def build_provider_tools(self) -> list[dict[str, Any] | ProviderToolSpec]:
        return [tool.to_dict() for tool in self.build_provider_tool_specs()]

    def build_provider_tool_specs(self) -> list[ProviderToolSpec]:
        provider_tools: list[ProviderToolSpec] = []
        for tool in self.tool_registry.list():
            provider_tools.append(
                ProviderToolSpec(
                    name=tool.definition.name,
                    description=tool.definition.description,
                    parameters=tuple(
                        ProviderToolParameter(
                            name=parameter.name,
                            type=parameter.type,
                            description=parameter.description,
                            required=parameter.required,
                            default=parameter.default,
                        )
                        for parameter in tool.definition.parameters
                    ),
                )
            )
        return provider_tools

    async def execute_tools(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        results: list[ToolResult] = []
        for call in tool_calls:
            self.emit(
                "before_tool",
                tool_name=call.name,
                arguments=call.arguments,
                tool_call_id=call.id,
                iteration=self.current_iteration(),
            )
            hook_decision: HookDecision | None = None
            agent_ctx = AgentContext(
                goal=self.context_manager.current_goal or "",
                step_count=self.current_iteration(),
                tool_name=call.name,
                tool_arguments=call.arguments,
            )
            hook_outcome = self.hook_manager.evaluate(
                "before_tool_call",
                {"tool": call.name, "arguments": call.arguments},
                agent_ctx,
            )
            hook_decision = hook_outcome.decision
            if hook_decision == HookDecision.DENY:
                result = ToolResult(
                    tool_call_id=call.id,
                    content=f"Hook denied: {hook_outcome.message}",
                    is_error=True,
                )
                results.append(result)
                self.emit(
                    "tool_result",
                    tool_name=call.name,
                    result=result.content,
                    success=False,
                    tool_call_id=call.id,
                )
                continue

            self.sync_governance_policy()
            result = await self.tool_executor.execute(call, hook_decision=hook_decision)
            results.append(result)
            self.emit(
                "tool_result",
                tool_name=call.name,
                result=result.content,
                success=not result.is_error,
                tool_call_id=call.id,
            )
        return results

    def sync_governance_policy(self) -> None:
        if hasattr(self.governance_policy, "tool_governance") and not getattr(
            self.governance_policy,
            "_uses_external_tool_governance",
            False,
        ):
            self.governance_policy.tool_governance = self.tool_governance
        if hasattr(self.governance_policy, "permission_manager") and not getattr(
            self.governance_policy,
            "_uses_external_permission_manager",
            False,
        ):
            self.governance_policy.permission_manager = self.permission_manager
        if hasattr(self.governance_policy, "veto_authority") and not getattr(
            self.governance_policy,
            "_uses_external_veto_authority",
            False,
        ):
            self.governance_policy.veto_authority = self.veto_authority
