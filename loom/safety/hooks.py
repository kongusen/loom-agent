"""Hook mechanism - 三层防护的第二层

Hook 规则：
- Hook deny 直接生效
- Hook ask 表示需要人工确认
- Hook allow 只能在权限层允许时生效
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


@dataclass
class AgentContext:
    """Rich agent state passed to hooks for informed decisions."""

    agent_id: str = ""
    goal: str = ""
    step_count: int = 0
    tool_name: str = ""
    tool_arguments: dict[str, Any] = field(default_factory=dict)
    execution_trace: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "goal": self.goal,
            "step_count": self.step_count,
            "tool_name": self.tool_name,
            "tool_arguments": self.tool_arguments,
            "execution_trace": self.execution_trace,
            **self.extra,
        }


class HookDecision(Enum):
    """Hook decision types."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass
class HookOutcome:
    """Structured hook result."""

    decision: HookDecision = HookDecision.ALLOW
    message: str = ""
    context_updates: dict[str, Any] = field(default_factory=dict)
    audit: dict[str, Any] = field(default_factory=dict)


class HookManager:
    """Manage execution hooks with ordered aggregation."""

    def __init__(self):
        self.hooks: dict[str, list[Callable]] = {}

    def register(self, event: str, callback: Callable):
        """Register hook."""
        if event not in self.hooks:
            self.hooks[event] = []
        self.hooks[event].append(callback)

    def trigger(
        self, event: str, context: dict, agent_context: AgentContext | None = None
    ) -> tuple[HookDecision, str]:
        """Trigger hooks, returning the legacy tuple API."""
        outcome = self.evaluate(event, context, agent_context)
        return outcome.decision, outcome.message

    def evaluate(
        self, event: str, context: dict[str, Any], agent_context: AgentContext | None = None
    ) -> HookOutcome:
        """Trigger hooks and return the aggregated outcome."""
        aggregated = HookOutcome()
        current_context = dict(context)
        if agent_context is not None:
            current_context.update(agent_context.to_dict())

        for hook in self.hooks.get(event, []):
            outcome = self._normalize(hook(current_context))

            if outcome.context_updates:
                current_context.update(outcome.context_updates)
                aggregated.context_updates.update(outcome.context_updates)

            if outcome.audit:
                aggregated.audit.update(outcome.audit)

            if outcome.decision == HookDecision.DENY:
                aggregated.decision = HookDecision.DENY
                aggregated.message = outcome.message or "Hook denied"
                return aggregated

            if outcome.decision == HookDecision.ASK:
                aggregated.decision = HookDecision.ASK
                if not aggregated.message:
                    aggregated.message = outcome.message or "Hook requests confirmation"

        return aggregated

    def _normalize(self, result: Any) -> HookOutcome:
        """Normalize common hook return shapes."""
        if isinstance(result, HookOutcome):
            return result
        if isinstance(result, HookDecision):
            return HookOutcome(decision=result)
        if isinstance(result, tuple) and result:
            decision = result[0]
            message = result[1] if len(result) > 1 else ""
            if isinstance(decision, HookDecision):
                return HookOutcome(decision=decision, message=str(message))
        if isinstance(result, dict):
            decision = result.get("decision", HookDecision.ALLOW)
            if isinstance(decision, str):
                decision = HookDecision(decision)
            return HookOutcome(
                decision=decision,
                message=str(result.get("message", "")),
                context_updates=dict(result.get("context_updates", {})),
                audit=dict(result.get("audit", {})),
            )
        return HookOutcome()
