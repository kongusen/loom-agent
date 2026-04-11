"""Tool executor with governance pipeline

治理流水线：Tool Request → Permission Check → Rate Limit → Execute → Observe
"""

from ..types import ToolCall, ToolResult
from ..utils.errors import ToolExecutionError, ToolNotFoundError, ToolPermissionError
from .governance import ToolGovernance
from .registry import ToolRegistry


class ToolExecutor:
    """Execute tools with governance pipeline"""

    def __init__(self, registry: ToolRegistry, governance: ToolGovernance | None = None):
        self.registry = registry
        self.governance = governance or ToolGovernance()

    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute a tool call with governance"""
        tool = self.registry.get(tool_call.name)

        if not tool:
            error = ToolNotFoundError(f"Tool not found: {tool_call.name}")
            return ToolResult(
                tool_call_id=tool_call.id,
                content=str(error),
                is_error=True
            )

        # Permission check (with parameter-level validation)
        ok, reason = self.governance.check_permission(
            tool_call.name,
            tool.definition,
            tool_call.arguments,
        )
        if not ok:
            error = ToolPermissionError(f"Permission denied: {reason}")
            return ToolResult(
                tool_call_id=tool_call.id,
                content=str(error),
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
            error = ToolExecutionError(f"Error: {str(e)}")
            return ToolResult(
                tool_call_id=tool_call.id,
                content=str(error),
                is_error=True
            )
