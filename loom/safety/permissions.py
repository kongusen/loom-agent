"""Permission system - 三层防护

权限模式：
- default: 遇到风险操作需要显式授权
- plan: 只能规划，不能执行
- auto: 自动决策（受信任场景）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .hooks import HookDecision


class PermissionMode(Enum):
    """Permission modes."""

    DEFAULT = "default"
    PLAN = "plan"
    AUTO = "auto"


@dataclass
class Permission:
    """Permission definition."""

    tool: str
    action: str
    allowed: bool = True
    mode: PermissionMode = PermissionMode.DEFAULT
    requires_approval: bool = False
    risk_levels: tuple[str, ...] = field(default_factory=tuple)
    note: str = ""


@dataclass
class PermissionDecision:
    """Structured permission evaluation result."""

    allowed: bool
    reason: str = ""
    requires_approval: bool = False
    matched_permission: Permission | None = None
    effective_mode: PermissionMode = PermissionMode.DEFAULT


class PermissionManager:
    """Manage tool permissions with explicit rules and mode-aware evaluation."""

    def __init__(self, mode: PermissionMode = PermissionMode.DEFAULT):
        self.permissions: dict[str, Permission] = {}
        self.mode = mode

    def grant(
        self,
        tool: str,
        action: str,
        *,
        requires_approval: bool = False,
        risk_levels: tuple[str, ...] | list[str] = (),
        note: str = "",
    ):
        """Grant permission."""
        permission = Permission(
            tool=tool,
            action=action,
            allowed=True,
            mode=self.mode,
            requires_approval=requires_approval,
            risk_levels=tuple(risk_levels),
            note=note,
        )
        self.permissions[self._key(tool, action)] = permission

    def revoke(self, tool: str, action: str, *, note: str = ""):
        """Revoke permission."""
        self.permissions[self._key(tool, action)] = Permission(
            tool=tool,
            action=action,
            allowed=False,
            mode=self.mode,
            note=note,
        )

    def check(
        self,
        tool: str,
        action: str,
        context: dict[str, Any] | None = None,
        hook_decision: HookDecision | None = None,
    ) -> tuple[bool, str]:
        """Check permission with mode and hook consideration."""
        decision = self.evaluate(tool, action, context=context, hook_decision=hook_decision)
        return decision.allowed, decision.reason

    def evaluate(
        self,
        tool: str,
        action: str,
        *,
        context: dict[str, Any] | None = None,
        hook_decision: HookDecision | None = None,
    ) -> PermissionDecision:
        """Return a structured permission decision."""
        context = context or {}

        if self.mode == PermissionMode.PLAN:
            return PermissionDecision(
                allowed=False,
                reason="Plan mode: execution not allowed",
                effective_mode=self.mode,
            )

        if hook_decision == HookDecision.DENY:
            return PermissionDecision(
                allowed=False,
                reason="Hook denied",
                effective_mode=self.mode,
            )

        permission = self._match_permission(tool, action)
        risk = str(context.get("risk", "")).lower()

        if permission is not None:
            if not permission.allowed:
                return PermissionDecision(
                    allowed=False,
                    reason=permission.note or "Permission denied",
                    matched_permission=permission,
                    effective_mode=self.mode,
                )

            if permission.risk_levels and risk in permission.risk_levels and self.mode != PermissionMode.AUTO:
                return PermissionDecision(
                    allowed=False,
                    reason=permission.note or f"Risk level {risk} requires approval",
                    requires_approval=True,
                    matched_permission=permission,
                    effective_mode=self.mode,
                )

            if (permission.requires_approval or hook_decision == HookDecision.ASK) and self.mode != PermissionMode.AUTO:
                return PermissionDecision(
                    allowed=False,
                    reason=permission.note or "Approval required",
                    requires_approval=True,
                    matched_permission=permission,
                    effective_mode=self.mode,
                )

            return PermissionDecision(
                allowed=True,
                reason="",
                matched_permission=permission,
                effective_mode=self.mode,
            )

        if hook_decision == HookDecision.ASK and self.mode != PermissionMode.AUTO:
            return PermissionDecision(
                allowed=False,
                reason="Hook requested confirmation",
                requires_approval=True,
                effective_mode=self.mode,
            )

        if self.mode == PermissionMode.AUTO:
            return PermissionDecision(
                allowed=True,
                reason="No explicit permission",
                effective_mode=self.mode,
            )

        if risk in {"high", "critical"}:
            return PermissionDecision(
                allowed=False,
                reason=f"Explicit permission required for {risk}-risk action",
                requires_approval=True,
                effective_mode=self.mode,
            )

        return PermissionDecision(
            allowed=False,
            reason="No explicit permission",
            effective_mode=self.mode,
        )

    def _match_permission(self, tool: str, action: str) -> Permission | None:
        """Match the most specific permission rule."""
        candidates = [
            self.permissions.get(self._key(tool, action)),
            self.permissions.get(self._key(tool, "*")),
            self.permissions.get(self._key("*", action)),
            self.permissions.get(self._key("*", "*")),
        ]
        for permission in candidates:
            if permission is not None:
                return permission
        return None

    def _key(self, tool: str, action: str) -> str:
        return f"{tool}:{action}"
