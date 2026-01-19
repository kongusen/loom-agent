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
