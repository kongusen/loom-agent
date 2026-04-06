"""Veto power - Ψ's final authority"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable


@dataclass
class VetoRule:
    """A named predicate that auto-vetoes matching tool calls."""

    name: str
    predicate: Callable[[str, dict[str, Any]], bool]  # (tool_name, args) -> should_veto
    reason: str


@dataclass
class VetoRecord:
    """Structured veto audit record."""

    reason: str
    tool: str | None = None
    action: str | None = None
    source: str = "system"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    context: dict[str, Any] = field(default_factory=dict)


class VetoAuthority:
    """Ψ's veto power (safety valve)."""

    def __init__(self):
        self.enabled = True
        self.veto_log: list[VetoRecord] = []
        self._rules: list[VetoRule] = []

    def add_rule(self, rule: VetoRule) -> None:
        """Register a veto rule."""
        self._rules.append(rule)

    def check_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> tuple[bool, str]:
        """Check tool call against all rules. Returns (vetoed, reason)."""
        if not self.enabled:
            return False, ""
        args = arguments or {}
        for rule in self._rules:
            if rule.predicate(tool_name, args):
                self.veto(rule.reason, tool=tool_name, source="rule:" + rule.name)
                return True, rule.reason
        return False, ""

    def veto(
        self,
        reason: str,
        *,
        tool: str | None = None,
        action: str | None = None,
        context: dict[str, Any] | None = None,
        source: str = "system",
    ) -> bool:
        """Exercise veto power."""
        if self.enabled:
            self.veto_log.append(
                VetoRecord(
                    reason=reason,
                    tool=tool,
                    action=action,
                    source=source,
                    context=dict(context or {}),
                )
            )
            return True
        return False

    def get_veto_history(self) -> list[str]:
        """Get veto history as reason strings for compatibility."""
        return [record.reason for record in self.veto_log]

    def get_veto_records(self) -> list[VetoRecord]:
        """Get structured veto records."""
        return list(self.veto_log)

    def audit_summary(self) -> dict[str, Any]:
        """Summarize veto activity for audit consumers."""
        return {
            "enabled": self.enabled,
            "count": len(self.veto_log),
            "sources": sorted({record.source for record in self.veto_log}),
            "tools": sorted({record.tool for record in self.veto_log if record.tool}),
        }
