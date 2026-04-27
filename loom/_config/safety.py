"""Configuration contracts for the public Loom API."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SafetyEvaluator:
    """Adapter for local callable-backed safety evaluation."""

    handler: Callable[[str, dict[str, Any]], bool]
    mode: str = "callable"
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def callable(
        cls,
        handler: Callable[[str, dict[str, Any]], bool],
        *,
        extensions: dict[str, Any] | None = None,
    ) -> SafetyEvaluator:
        return cls(handler=handler, mode="callable", extensions=dict(extensions or {}))

    def evaluate(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        return bool(self.handler(tool_name, arguments))


@dataclass(slots=True)
class SafetyRule:
    """Public declarative safety rule."""

    name: str
    reason: str
    tool_names: list[str] = field(default_factory=list)
    arg_equals: dict[str, Any] = field(default_factory=dict)
    arg_prefixes: dict[str, str] = field(default_factory=dict)
    arg_contains_any: dict[str, list[str]] = field(default_factory=dict)
    evaluator: SafetyEvaluator | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def block_tool(
        cls,
        *,
        name: str,
        tool_names: list[str],
        reason: str,
        extensions: dict[str, Any] | None = None,
    ) -> SafetyRule:
        return cls(
            name=name,
            reason=reason,
            tool_names=list(tool_names),
            extensions=dict(extensions or {}),
        )

    @classmethod
    def when_argument_equals(
        cls,
        *,
        name: str,
        tool_name: str,
        argument: str,
        value: Any,
        reason: str,
        extensions: dict[str, Any] | None = None,
    ) -> SafetyRule:
        return cls(
            name=name,
            reason=reason,
            tool_names=[tool_name],
            arg_equals={argument: value},
            extensions=dict(extensions or {}),
        )

    @classmethod
    def when_argument_startswith(
        cls,
        *,
        name: str,
        tool_name: str,
        argument: str,
        prefix: str,
        reason: str,
        extensions: dict[str, Any] | None = None,
    ) -> SafetyRule:
        return cls(
            name=name,
            reason=reason,
            tool_names=[tool_name],
            arg_prefixes={argument: prefix},
            extensions=dict(extensions or {}),
        )

    @classmethod
    def when_argument_contains_any(
        cls,
        *,
        name: str,
        tool_name: str,
        argument: str,
        values: list[str],
        reason: str,
        extensions: dict[str, Any] | None = None,
    ) -> SafetyRule:
        return cls(
            name=name,
            reason=reason,
            tool_names=[tool_name],
            arg_contains_any={argument: list(values)},
            extensions=dict(extensions or {}),
        )

    @classmethod
    def custom(
        cls,
        *,
        name: str,
        reason: str,
        evaluator: SafetyEvaluator,
        tool_names: list[str] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> SafetyRule:
        return cls(
            name=name,
            reason=reason,
            tool_names=list(tool_names or []),
            evaluator=evaluator,
            extensions=dict(extensions or {}),
        )

    def matches(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        if self.tool_names and tool_name not in self.tool_names:
            return False

        for argument, expected in self.arg_equals.items():
            if arguments.get(argument) != expected:
                return False

        for argument, prefix in self.arg_prefixes.items():
            if not str(arguments.get(argument, "")).startswith(prefix):
                return False

        for argument, values in self.arg_contains_any.items():
            candidate = str(arguments.get(argument, ""))
            if not any(value in candidate for value in values):
                return False

        if self.evaluator is not None and not self.evaluator.evaluate(tool_name, arguments):
            return False

        return bool(
            self.tool_names
            or self.arg_equals
            or self.arg_prefixes
            or self.arg_contains_any
            or self.evaluator is not None
        )
