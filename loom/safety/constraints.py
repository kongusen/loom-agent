"""Constraint validator - O = Σ × Constraint"""

from ..types import ToolCall


class ConstraintValidator:
    """Validate tool calls against constraints"""

    def __init__(self):
        self.constraints: dict[str, list] = {}

    def add_constraint(self, tool: str, constraint):
        """Add constraint for tool"""
        if tool not in self.constraints:
            self.constraints[tool] = []
        self.constraints[tool].append(constraint)

    def validate(self, tool_call: ToolCall) -> tuple[bool, str]:
        """Validate tool call"""
        constraints = self.constraints.get(tool_call.name, [])
        for constraint in constraints:
            if not constraint(tool_call):
                return False, f"Constraint violation for {tool_call.name}"
        return True, ""
