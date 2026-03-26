"""Constraint validator — pre-execution validation (Harness P0)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..scene import SceneManager
    from ..types import ToolCall


class ConstraintValidator:
    """前置约束验证 - 在工具调用前验证所有约束."""

    def __init__(self, scene_mgr: SceneManager) -> None:
        self._scene_mgr = scene_mgr
        self._violations: list[dict] = []

    def validate_before_call(self, tool_call: ToolCall) -> tuple[bool, str]:
        """调用前验证 - 快速失败.

        Returns:
            (is_valid, error_message)
        """
        if not self._scene_mgr.current:
            return True, ""

        # 工具白名单检查
        if not self._scene_mgr.is_tool_allowed(tool_call.name):
            self._record_violation(tool_call.name, "whitelist", "Tool not in scene whitelist")
            return False, f"Tool '{tool_call.name}' not allowed in scene '{self._scene_mgr.current.id}'"

        # 约束检查
        constraints = self._scene_mgr.current.constraints

        if constraints.get("network") is False and tool_call.name in ["web_search", "web_fetch", "http_request"]:
            self._record_violation(tool_call.name, "network", "Network disabled")
            return False, "Network access disabled in current scene"

        if constraints.get("write") is False and tool_call.name in ["write_file", "bash", "file_write"]:
            self._record_violation(tool_call.name, "write", "Write disabled")
            return False, "Write access disabled in current scene"

        if constraints.get("read") is False and tool_call.name in ["read_file", "file_read"]:
            self._record_violation(tool_call.name, "read", "Read disabled")
            return False, "Read access disabled in current scene"

        return True, ""

    def _record_violation(self, tool_name: str, constraint_type: str, reason: str) -> None:
        """记录违规用于审计."""
        self._violations.append({
            "timestamp": time.time(),
            "tool": tool_name,
            "constraint": constraint_type,
            "reason": reason,
        })

    def get_violations(self) -> list[dict]:
        """获取违规记录."""
        return self._violations

    def clear_violations(self) -> None:
        """清空违规记录."""
        self._violations.clear()
