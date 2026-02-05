"""
Loom Agent Exceptions
"""


class LoomError(Exception):
    """Base exception for all Loom errors."""

    pass


class TaskComplete(LoomError):
    """
    Raised when a task is completed by the agent using the 'done' tool.

    Attributes:
        message: The completion message summarizing what was accomplished.
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(f"Task completed: {message}")


class PermissionDenied(LoomError):
    """
    Raised when a tool execution is denied by the ToolPolicy.

    Attributes:
        tool_name: The name of the tool that was denied.
        reason: The reason for denial.
    """

    def __init__(self, tool_name: str, reason: str = ""):
        self.tool_name = tool_name
        self.reason = reason
        message = f"PERMISSION_MISSING: Tool '{tool_name}' is not allowed"
        if reason:
            message += f" - {reason}"
        super().__init__(message)
