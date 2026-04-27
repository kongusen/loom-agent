"""Tool executor with governance pipeline

治理流水线：Tool Request → Permission Check → Rate Limit → Execute → Observe
"""

from typing import TYPE_CHECKING

from ..safety.hooks import HookDecision
from ..types import ToolCall, ToolResult
from ..utils.errors import ToolExecutionError, ToolNotFoundError, ToolPermissionError
from .governance import ToolGovernance
from .registry import ToolRegistry

if TYPE_CHECKING:
    from ..runtime.governance import RuntimeGovernancePolicy


class ToolExecutor:
    """Execute tools with governance pipeline"""

    def __init__(
        self,
        registry: ToolRegistry,
        governance: ToolGovernance | None = None,
        governance_policy: "RuntimeGovernancePolicy | None" = None,
    ):
        self.registry = registry
        self.governance = governance or ToolGovernance()
        self.governance_policy = governance_policy

    async def execute(
        self,
        tool_call: ToolCall,
        *,
        hook_decision: HookDecision | None = None,
    ) -> ToolResult:
        """Execute a tool call with governance"""
        tool = self.registry.get(tool_call.name)

        if not tool:
            if self.governance_policy is not None:
                from ..runtime.governance import GovernanceRequest

                request = GovernanceRequest(
                    tool_name=tool_call.name,
                    action="execute",
                    arguments=tool_call.arguments,
                    hook_decision=hook_decision,
                )
                decision = self.governance_policy.evaluate_tool(request)
                if not decision.allowed:
                    return ToolResult(
                        tool_call_id=tool_call.id,
                        content=self._denied_content(decision.reason, decision.source),
                        is_error=True,
                    )

            error = ToolNotFoundError(f"Tool not found: {tool_call.name}")
            return ToolResult(
                tool_call_id=tool_call.id,
                content=str(error),
                is_error=True
            )

        if self.governance_policy is not None:
            from ..runtime.governance import GovernanceRequest

            request = GovernanceRequest(
                tool_name=tool_call.name,
                action="execute",
                arguments=tool_call.arguments,
                tool_definition=tool.definition,
                hook_decision=hook_decision,
            )
            decision = self.governance_policy.evaluate_tool(request)
            if not decision.allowed:
                return ToolResult(
                    tool_call_id=tool_call.id,
                    content=self._denied_content(decision.reason, decision.source),
                    is_error=True,
                )

            try:
                result = await tool.execute(**tool_call.arguments)
                self.governance_policy.record_tool_result(request, success=True)
                return ToolResult(
                    tool_call_id=tool_call.id,
                    content=str(result),
                    is_error=False,
                )
            except Exception as e:
                self.governance_policy.record_tool_result(request, success=False)
                return ToolResult(
                    tool_call_id=tool_call.id,
                    content=str(ToolExecutionError(f"Error: {str(e)}")),
                    is_error=True,
                )

        # Permission check (with parameter-level validation)
        ok, reason = self.governance.check_permission(
            tool_call.name,
            tool.definition,
            tool_call.arguments,
        )
        if not ok:
            return ToolResult(
                tool_call_id=tool_call.id,
                content=str(ToolPermissionError(f"Permission denied: {reason}")),
                is_error=True
            )

        # Rate limit check
        ok, reason = self.governance.check_rate_limit(tool_call.name)
        if not ok:
            return ToolResult(
                tool_call_id=tool_call.id,
                content=f"Rate limit: {reason}",
                is_error=True
            )

        # Execute
        try:
            result = await tool.execute(**tool_call.arguments)
            self.governance.record_call(tool_call.name)
            return ToolResult(
                tool_call_id=tool_call.id,
                content=str(result),
                is_error=False
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id,
                content=str(ToolExecutionError(f"Error: {str(e)}")),
                is_error=True
            )

    def _denied_content(self, reason: str, source: str) -> str:
        if source == "veto":
            return f"Vetoed: {reason}"
        return str(ToolPermissionError(f"Permission denied: {reason}"))
