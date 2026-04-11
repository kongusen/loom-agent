"""Feedback loop for evolution"""


class FeedbackLoop:
    """Collect and process feedback"""

    def __init__(self):
        self.feedback: list[dict] = []

    def add_feedback(self, feedback: dict):
        """Add feedback"""
        self.feedback.append(feedback)

    def get_feedback(self) -> list[dict]:
        """Get all feedback"""
        return self.feedback

    def subscribe_to_engine(self, engine) -> None:
        """Subscribe to runtime engine tool-result events."""
        subscribe = getattr(engine, "on", None)
        if not callable(subscribe):
            raise TypeError("engine does not support event subscription")
        subscribe("tool_result", self._on_tool_result)

    def _on_tool_result(
        self,
        *,
        tool_name: str,
        result: str,
        success: bool,
        tool_call_id: str | None = None,
        **_unused,
    ) -> None:
        """Project runtime tool results into evolution feedback entries."""
        self.add_feedback(
            {
                "tool": tool_name,
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "type": "success" if success else "failure",
                "success": success,
                "result": result,
            }
        )
