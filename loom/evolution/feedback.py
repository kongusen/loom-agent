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
