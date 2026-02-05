"""
ToolPolicy 单元测试

测试工具权限策略功能
"""

from loom.exceptions import PermissionDenied
from loom.security.tool_policy import BlacklistPolicy, ToolContext, WhitelistPolicy


class TestPermissionDenied:
    """测试 PermissionDenied 异常"""

    def test_permission_denied_basic(self):
        """测试基本的 PermissionDenied 异常"""
        exc = PermissionDenied(tool_name="dangerous_tool")

        assert exc.tool_name == "dangerous_tool"
        assert exc.reason == ""
        assert "PERMISSION_MISSING" in str(exc)
        assert "dangerous_tool" in str(exc)

    def test_permission_denied_with_reason(self):
        """测试带原因的 PermissionDenied 异常"""
        exc = PermissionDenied(tool_name="dangerous_tool", reason="Tool not in whitelist")

        assert exc.tool_name == "dangerous_tool"
        assert exc.reason == "Tool not in whitelist"
        assert "PERMISSION_MISSING" in str(exc)
        assert "dangerous_tool" in str(exc)
        assert "Tool not in whitelist" in str(exc)


class TestWhitelistPolicy:
    """测试 WhitelistPolicy"""

    def test_whitelist_allows_listed_tools(self):
        """测试白名单允许列表中的工具"""
        policy = WhitelistPolicy(allowed_tools={"tool1", "tool2", "tool3"})

        assert policy.is_allowed(ToolContext(tool_name="tool1")) is True
        assert policy.is_allowed(ToolContext(tool_name="tool2")) is True
        assert policy.is_allowed(ToolContext(tool_name="tool3")) is True

    def test_whitelist_denies_unlisted_tools(self):
        """测试白名单拒绝不在列表中的工具"""
        policy = WhitelistPolicy(allowed_tools={"tool1", "tool2"})

        assert policy.is_allowed(ToolContext(tool_name="tool3")) is False
        assert policy.is_allowed(ToolContext(tool_name="dangerous_tool")) is False

    def test_whitelist_denial_reason(self):
        """测试白名单拒绝原因"""
        policy = WhitelistPolicy(allowed_tools={"tool1", "tool2"})

        reason = policy.get_denial_reason(ToolContext(tool_name="tool3"))

        assert "whitelist" in reason.lower()
        assert "tool1" in reason
        assert "tool2" in reason

    def test_whitelist_empty_set(self):
        """测试空白名单（拒绝所有工具）"""
        policy = WhitelistPolicy(allowed_tools=set())

        assert policy.is_allowed(ToolContext(tool_name="any_tool")) is False


class TestBlacklistPolicy:
    """测试 BlacklistPolicy"""

    def test_blacklist_denies_listed_tools(self):
        """测试黑名单拒绝列表中的工具"""
        policy = BlacklistPolicy(forbidden_tools={"dangerous1", "dangerous2"})

        assert policy.is_allowed(ToolContext(tool_name="dangerous1")) is False
        assert policy.is_allowed(ToolContext(tool_name="dangerous2")) is False

    def test_blacklist_allows_unlisted_tools(self):
        """测试黑名单允许不在列表中的工具"""
        policy = BlacklistPolicy(forbidden_tools={"dangerous1", "dangerous2"})

        assert policy.is_allowed(ToolContext(tool_name="safe_tool")) is True
        assert policy.is_allowed(ToolContext(tool_name="another_tool")) is True

    def test_blacklist_denial_reason(self):
        """测试黑名单拒绝原因"""
        policy = BlacklistPolicy(forbidden_tools={"dangerous1", "dangerous2"})

        reason = policy.get_denial_reason(ToolContext(tool_name="dangerous1"))

        assert "forbidden" in reason.lower() or "blacklist" in reason.lower()
        assert "dangerous1" in reason

    def test_blacklist_empty_set(self):
        """测试空黑名单（允许所有工具）"""
        policy = BlacklistPolicy(forbidden_tools=set())

        assert policy.is_allowed(ToolContext(tool_name="any_tool")) is True
