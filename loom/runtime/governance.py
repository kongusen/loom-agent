"""Runtime governance policy contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from ..safety.hooks import HookDecision
from ..safety.permissions import PermissionManager
from ..safety.veto import VetoAuthority
from ..tools.governance import ToolGovernance

if TYPE_CHECKING:
    from ..tools.schema import ToolDefinition


@dataclass(slots=True)
class GovernanceDecision:
    """Normalized decision for a guarded runtime action."""

    allowed: bool
    reason: str = ""
    source: str = "governance"
    requires_approval: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GovernanceRequest:
    """One tool execution request evaluated by a governance policy."""

    tool_name: str
    action: str = "execute"
    arguments: dict[str, Any] = field(default_factory=dict)
    tool_definition: ToolDefinition | None = None
    hook_decision: HookDecision | None = None
    context: dict[str, Any] = field(default_factory=dict)


class RuntimeGovernancePolicy(Protocol):
    """Protocol implemented by runtime governance policies."""

    def evaluate_tool(self, request: GovernanceRequest) -> GovernanceDecision: ...

    def record_tool_result(self, request: GovernanceRequest, *, success: bool) -> None: ...


class GovernancePolicy:
    """Factory for built-in runtime governance policies."""

    @staticmethod
    def default(
        *,
        tool_governance: ToolGovernance | None = None,
        permission_manager: PermissionManager | None = None,
        veto_authority: VetoAuthority | None = None,
    ) -> DefaultGovernancePolicy:
        return DefaultGovernancePolicy(
            tool_governance=tool_governance,
            permission_manager=permission_manager,
            veto_authority=veto_authority,
        )

    @staticmethod
    def allow_all() -> AllowAllGovernancePolicy:
        return AllowAllGovernancePolicy()

    @staticmethod
    def deny_all(reason: str = "Denied by governance policy") -> DenyAllGovernancePolicy:
        return DenyAllGovernancePolicy(reason)


class DefaultGovernancePolicy:
    """Adapter that unifies permissions, veto, and tool governance."""

    def __init__(
        self,
        *,
        tool_governance: ToolGovernance | None = None,
        permission_manager: PermissionManager | None = None,
        veto_authority: VetoAuthority | None = None,
    ) -> None:
        self._uses_external_tool_governance = tool_governance is not None
        self._uses_external_permission_manager = permission_manager is not None
        self._uses_external_veto_authority = veto_authority is not None
        self.tool_governance = tool_governance or ToolGovernance()
        self.permission_manager = permission_manager
        self.veto_authority = veto_authority

    def evaluate_tool(self, request: GovernanceRequest) -> GovernanceDecision:
        permission = self._check_permission_manager(request)
        if permission is not None:
            return permission

        veto = self._check_veto(request)
        if veto is not None:
            return veto

        tool_permission = self._check_tool_governance(request)
        if tool_permission is not None:
            return tool_permission

        rate_limit = self._check_rate_limit(request)
        if rate_limit is not None:
            return rate_limit

        return GovernanceDecision(allowed=True)

    def record_tool_result(self, request: GovernanceRequest, *, success: bool) -> None:
        if success:
            self.tool_governance.record_call(request.tool_name)

    def _check_permission_manager(
        self,
        request: GovernanceRequest,
    ) -> GovernanceDecision | None:
        if self.permission_manager is None:
            return None
        decision = self.permission_manager.evaluate(
            request.tool_name,
            request.action,
            context={
                "arguments": request.arguments,
                **request.context,
            },
            hook_decision=request.hook_decision,
        )
        if decision.allowed:
            return None
        return GovernanceDecision(
            allowed=False,
            reason=decision.reason,
            source="permission",
            requires_approval=decision.requires_approval,
            metadata={"mode": decision.effective_mode.value},
        )

    def _check_veto(self, request: GovernanceRequest) -> GovernanceDecision | None:
        if self.veto_authority is None:
            return None
        vetoed, reason = self.veto_authority.check_tool(
            request.tool_name,
            request.arguments,
        )
        if not vetoed:
            return None
        return GovernanceDecision(
            allowed=False,
            reason=reason,
            source="veto",
        )

    def _check_tool_governance(
        self,
        request: GovernanceRequest,
    ) -> GovernanceDecision | None:
        ok, reason = self.tool_governance.check_permission(
            request.tool_name,
            request.tool_definition,
            request.arguments,
        )
        if ok:
            return None
        return GovernanceDecision(
            allowed=False,
            reason=reason,
            source="tool_governance",
        )

    def _check_rate_limit(self, request: GovernanceRequest) -> GovernanceDecision | None:
        ok, reason = self.tool_governance.check_rate_limit(request.tool_name)
        if ok:
            return None
        return GovernanceDecision(
            allowed=False,
            reason=reason,
            source="rate_limit",
        )


class AllowAllGovernancePolicy:
    """Governance policy for trusted tests and fully delegated environments."""

    def evaluate_tool(self, request: GovernanceRequest) -> GovernanceDecision:
        _ = request
        return GovernanceDecision(allowed=True, source="allow_all")

    def record_tool_result(self, request: GovernanceRequest, *, success: bool) -> None:
        _ = request
        _ = success


class DenyAllGovernancePolicy:
    """Governance policy that denies every tool request."""

    def __init__(self, reason: str) -> None:
        self.reason = reason

    def evaluate_tool(self, request: GovernanceRequest) -> GovernanceDecision:
        _ = request
        return GovernanceDecision(
            allowed=False,
            reason=self.reason,
            source="deny_all",
        )

    def record_tool_result(self, request: GovernanceRequest, *, success: bool) -> None:
        _ = request
        _ = success
