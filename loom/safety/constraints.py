"""Constraint validator - O = Σ × Constraint"""

from dataclasses import dataclass, field
from typing import Any

from ..types import ToolCall


@dataclass(slots=True)
class ConstraintViolation:
    """Structured violation details for constraint failures."""

    tool: str
    constraint_index: int
    message: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ConstraintValidationResult:
    """Constraint validation outcome with full diagnostics."""

    ok: bool
    message: str = ""
    violations: list[ConstraintViolation] = field(default_factory=list)


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
        result = self.validate_with_details(tool_call)
        return result.ok, result.message

    def validate_with_details(self, tool_call: ToolCall) -> ConstraintValidationResult:
        """Validate tool call and return structured diagnostics."""
        constraints = self.constraints.get(tool_call.name, [])
        violations: list[ConstraintViolation] = []
        for index, constraint in enumerate(constraints):
            try:
                verdict = constraint(tool_call)
            except Exception as exc:
                violations.append(
                    ConstraintViolation(
                        tool=tool_call.name,
                        constraint_index=index,
                        message=f"Constraint exception: {exc}",
                        arguments=dict(tool_call.arguments),
                    )
                )
                continue

            ok = bool(verdict[0]) if isinstance(verdict, tuple) else bool(verdict)
            if ok:
                continue
            reason = (
                str(verdict[1])
                if isinstance(verdict, tuple) and len(verdict) > 1
                else f"Constraint violation for {tool_call.name}"
            )
            violations.append(
                ConstraintViolation(
                    tool=tool_call.name,
                    constraint_index=index,
                    message=reason,
                    arguments=dict(tool_call.arguments),
                )
            )

        if violations:
            return ConstraintValidationResult(
                ok=False,
                message=violations[0].message,
                violations=violations,
            )
        return ConstraintValidationResult(ok=True)
