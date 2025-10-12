from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Dict, Optional


class PermissionAction(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


ConfirmHandler = Callable[[str, Dict[str, Any]], bool]


class PermissionManager:
    """最小权限网关：按工具名匹配 allow/deny/ask。"""

    def __init__(
        self,
        policy: Optional[Dict[str, str]] = None,
        default: str = "deny",
        ask_handler: Optional[ConfirmHandler] = None,
    ) -> None:
        self.policy = {**(policy or {})}
        self.default = default
        self.ask_handler = ask_handler

    def check(self, tool_name: str, arguments: Dict[str, Any]) -> PermissionAction:
        action = self.policy.get(tool_name, self.policy.get("default", self.default))
        try:
            return PermissionAction(action)
        except Exception:
            return PermissionAction.DENY

    def confirm(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        if not self.ask_handler:
            return False
        return bool(self.ask_handler(tool_name, arguments))

