"""Tool governance pipeline with fine-grained parameter-level control"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .schema import ToolDefinition


@dataclass(slots=True)
class ConstraintViolation:
    """Structured parameter-constraint violation details."""

    constraint_type: str
    parameter: str
    message: str
    value: Any


@dataclass
class ParameterConstraint:
    """Parameter-level constraint for fine-grained control"""
    parameter_name: str
    constraint_type: str  # "regex", "range", "enum", "custom"
    constraint_value: Any
    error_message: str = ""

    def validate(self, value: Any) -> tuple[bool, str]:
        """Validate parameter value against constraint"""
        if self.constraint_type == "regex":
            if not isinstance(value, str):
                return False, f"{self.parameter_name} must be string for regex validation"
            pattern = self.constraint_value
            if not re.match(pattern, value):
                msg = self.error_message or f"{self.parameter_name} does not match pattern {pattern}"
                return False, msg

        elif self.constraint_type == "range":
            min_val, max_val = self.constraint_value
            if not isinstance(value, int | float):
                return False, f"{self.parameter_name} must be numeric for range validation"
            if not (min_val <= value <= max_val):
                msg = self.error_message or f"{self.parameter_name} must be between {min_val} and {max_val}"
                return False, msg

        elif self.constraint_type == "enum":
            allowed_values = self.constraint_value
            if value not in allowed_values:
                msg = self.error_message or f"{self.parameter_name} must be one of {allowed_values}"
                return False, msg

        elif self.constraint_type == "custom":
            validator_fn = self.constraint_value
            if not callable(validator_fn):
                return False, f"Custom validator for {self.parameter_name} is not callable"
            try:
                result = validator_fn(value)
                if isinstance(result, tuple):
                    return result
                elif isinstance(result, bool):
                    return result, self.error_message or f"{self.parameter_name} validation failed"
                else:
                    return False, f"Invalid validator return type for {self.parameter_name}"
            except Exception as e:
                return False, f"Validator error for {self.parameter_name}: {str(e)}"

        return True, ""

    def violation(self, value: Any) -> ConstraintViolation | None:
        """Return a structured violation object when validation fails."""
        ok, reason = self.validate(value)
        if ok:
            return None
        return ConstraintViolation(
            constraint_type=self.constraint_type,
            parameter=self.parameter_name,
            message=reason,
            value=value,
        )


@dataclass
class ToolPolicy:
    """Tool-specific policy with parameter constraints"""
    tool_name: str
    parameter_constraints: list[ParameterConstraint] = field(default_factory=list)
    max_calls_per_minute: int | None = None  # Tool-specific rate limit
    require_confirmation: bool = False  # Require user confirmation
    allowed_contexts: set[str] = field(default_factory=set)  # e.g., {"development", "production"}
    custom_policy: Callable[[str, dict[str, Any], Any], tuple[bool, str]] | None = None


@dataclass
class GovernanceConfig:
    """Governance configuration with fine-grained control"""
    # Basic settings
    enable_rate_limit: bool = True
    enable_permission_check: bool = True
    enable_parameter_validation: bool = True
    max_calls_per_minute: int = 60

    # Tool-level controls
    allow_tools: set[str] = field(default_factory=set)
    deny_tools: set[str] = field(default_factory=set)
    read_only_only: bool = False
    allow_destructive: bool = False
    default_allow: bool = True

    # Fine-grained controls
    tool_policies: dict[str, ToolPolicy] = field(default_factory=dict)
    current_context: str = "default"  # Current execution context

    # Context-aware decision making
    context_policy: Callable[[str, str, dict[str, Any], Any], tuple[bool, str]] | None = None


class ToolGovernance:
    """Tool governance pipeline with fine-grained parameter-level control"""

    def __init__(self, config: GovernanceConfig | None = None, runtime_context: Any = None):
        self.config = config or GovernanceConfig()
        self.call_counts: dict[str, int] = {}
        self.runtime_context = runtime_context  # Dashboard, Agent state, etc.
        self._last_parameter_violations: list[ConstraintViolation] = []

    def check_permission(
        self,
        tool_name: str,
        tool_definition: ToolDefinition | None = None,
        arguments: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        """Check if tool execution is allowed with fine-grained parameter validation"""
        self._last_parameter_violations = []
        if not self.config.enable_permission_check:
            return True, ""

        # 1. Basic tool-level checks (existing logic)
        if tool_name in self.config.deny_tools:
            return False, f"{tool_name} is explicitly denied"

        if self.config.allow_tools and tool_name not in self.config.allow_tools:
            return False, f"{tool_name} is not in allowlist"

        # Check tool definition properties if available
        if tool_definition is not None:
            if self.config.read_only_only and not tool_definition.is_read_only:
                return False, f"{tool_name} is not read-only"

            if tool_definition.is_destructive and not self.config.allow_destructive:
                return False, f"{tool_name} is destructive and destructive tools are disabled"

        # 2. Tool-specific policy checks (new) - check even without tool_definition
        tool_policy = self.config.tool_policies.get(tool_name)
        if tool_policy:
            # Check context restrictions
            if tool_policy.allowed_contexts and self.config.current_context not in tool_policy.allowed_contexts:
                return False, f"{tool_name} not allowed in context '{self.config.current_context}'"

            # Check parameter constraints
            if self.config.enable_parameter_validation and arguments:
                ok, reason = self._validate_parameters(tool_name, tool_policy, arguments)
                if not ok:
                    return False, reason

            # Check custom policy
            if tool_policy.custom_policy:
                try:
                    ok, reason = tool_policy.custom_policy(tool_name, arguments or {}, self.runtime_context)
                    if not ok:
                        return False, reason
                except Exception as e:
                    return False, f"Custom policy error for {tool_name}: {str(e)}"

        # 3. Context-aware global policy (new)
        if self.config.context_policy and arguments:
            try:
                ok, reason = self.config.context_policy(
                    tool_name,
                    self.config.current_context,
                    arguments,
                    self.runtime_context
                )
                if not ok:
                    return False, reason
            except Exception as e:
                return False, f"Context policy error: {str(e)}"

        # 4. Default policy if no tool_definition and no specific policies
        if tool_definition is None and not tool_policy and not self.config.context_policy:
            return self.config.default_allow, (
                "" if self.config.default_allow else f"{tool_name} denied by default policy"
            )

        return True, ""

    def _validate_parameters(
        self,
        tool_name: str,
        tool_policy: ToolPolicy,
        arguments: dict[str, Any]
    ) -> tuple[bool, str]:
        """Validate parameters against constraints"""
        violations: list[ConstraintViolation] = []
        for constraint in tool_policy.parameter_constraints:
            param_name = constraint.parameter_name
            if param_name not in arguments:
                continue  # Skip if parameter not provided

            value = arguments[param_name]
            violation = constraint.violation(value)
            if violation is not None:
                violations.append(violation)

        self._last_parameter_violations = violations
        if violations:
            first = violations[0]
            return (
                False,
                f"{tool_name}: {first.message} "
                f"[parameter={first.parameter}, constraint={first.constraint_type}, value={first.value!r}]",
            )

        return True, ""

    def get_last_parameter_violations(self) -> list[ConstraintViolation]:
        """Return structured violations from the last permission check."""
        return list(self._last_parameter_violations)

    def check_rate_limit(self, tool_name: str) -> tuple[bool, str]:
        """Check rate limit with tool-specific overrides"""
        if not self.config.enable_rate_limit:
            return True, ""

        # Check tool-specific rate limit first
        tool_policy = self.config.tool_policies.get(tool_name)
        if tool_policy and tool_policy.max_calls_per_minute is not None:
            limit = tool_policy.max_calls_per_minute
        else:
            limit = self.config.max_calls_per_minute

        count = self.call_counts.get(tool_name, 0)
        if count >= limit:
            return False, f"Rate limit exceeded for {tool_name} ({count}/{limit} calls)"

        return True, ""

    def record_call(self, tool_name: str) -> None:
        """Record a successful tool call."""
        self.call_counts[tool_name] = self.call_counts.get(tool_name, 0) + 1

    def reset_rate_limits(self) -> None:
        """Reset all rate limit counters (call periodically, e.g., every minute)"""
        self.call_counts.clear()

    def set_context(self, context: str) -> None:
        """Update current execution context"""
        self.config.current_context = context

    def update_runtime_context(self, runtime_context: Any) -> None:
        """Update runtime context (Dashboard, Agent state, etc.)"""
        self.runtime_context = runtime_context
