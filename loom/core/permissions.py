from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Dict, Optional
from .permission_store import PermissionStore


class PermissionAction(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


ConfirmHandler = Callable[[str, Dict[str, Any]], bool]


class PermissionManager:
    """权限网关（框架能力）：
    - 默认策略(policy/default)
    - 可选安全模式：启用后优先通过持久化允许列表( PermissionStore ) 进行放行；否则 ASK。
    - 用户确认通过后可持久化授权。
    """

    def __init__(
        self,
        policy: Optional[Dict[str, str]] = None,
        default: str = "deny",
        ask_handler: Optional[ConfirmHandler] = None,
        *,
        safe_mode: bool = False,
        permission_store: Optional[PermissionStore] = None,
        persist_on_approve: bool = True,
    ) -> None:
        self.policy = {**(policy or {})}
        self.default = default
        self.ask_handler = ask_handler
        self.safe_mode = safe_mode
        self.permission_store = permission_store or PermissionStore.load_default()
        self.persist_on_approve = persist_on_approve

    def _policy_action(self, tool_name: str) -> PermissionAction:
        action = self.policy.get(tool_name, self.policy.get("default", self.default))
        try:
            return PermissionAction(action)
        except Exception:
            return PermissionAction.DENY

    def check(self, tool_name: str, arguments: Dict[str, Any]) -> PermissionAction:
        # 1) Policy precedence
        policy_action = self._policy_action(tool_name)
        if not self.safe_mode:
            return policy_action

        # safe_mode enabled
        if policy_action in (PermissionAction.ALLOW, PermissionAction.DENY):
            return policy_action

        # ASK or unspecified → consult store
        if self.permission_store.is_allowed(tool_name):
            return PermissionAction.ALLOW
        return PermissionAction.ASK

    def confirm(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        approved = bool(self.ask_handler(tool_name, arguments)) if self.ask_handler else False
        if approved and self.safe_mode and self.persist_on_approve and self.permission_store:
            # persist allow for this tool
            self.permission_store.grant(tool_name)
            self.permission_store.save()
        return approved
