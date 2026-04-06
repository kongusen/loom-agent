"""Test security module - guard, permissions, hooks"""

import pytest

from loom.security.permissions import PermissionManager, Permission
from loom.security.hooks import HookManager, HookResult
from loom.security.guard import SecurityGuard


# ── Permission ──

class TestPermission:
    def test_creation(self):
        perm = Permission(name="read_files", level="read", resource="filesystem")
        assert perm.name == "read_files"
        assert perm.level == "read"
        assert perm.resource == "filesystem"


# ── PermissionManager ──

class TestPermissionManager:
    def test_creation(self):
        pm = PermissionManager()
        assert pm.permissions == {}

    def test_grant(self):
        pm = PermissionManager()
        perm = Permission(name="read", level="read", resource="files")
        pm.grant("user_1", perm)
        assert "user_1" in pm.permissions
        assert len(pm.permissions["user_1"]) == 1
        assert pm.permissions["user_1"][0] is perm

    def test_grant_multiple(self):
        pm = PermissionManager()
        pm.grant("user_1", Permission(name="r", level="read", resource="files"))
        pm.grant("user_1", Permission(name="w", level="write", resource="files"))
        assert len(pm.permissions["user_1"]) == 2

    def test_grant_different_users(self):
        pm = PermissionManager()
        pm.grant("user_1", Permission(name="r", level="read", resource="files"))
        pm.grant("user_2", Permission(name="w", level="write", resource="files"))
        assert len(pm.permissions) == 2

    def test_check_allowed(self):
        pm = PermissionManager()
        pm.grant("user_1", Permission(name="r", level="read", resource="files"))
        assert pm.check("user_1", "files", "read") is True

    def test_check_higher_level_grants_lower(self):
        pm = PermissionManager()
        pm.grant("user_1", Permission(name="admin", level="admin", resource="files"))
        assert pm.check("user_1", "files", "read") is True
        assert pm.check("user_1", "files", "write") is True
        assert pm.check("user_1", "files", "execute") is True
        assert pm.check("user_1", "files", "admin") is True

    def test_check_lower_level_denies_higher(self):
        pm = PermissionManager()
        pm.grant("user_1", Permission(name="r", level="read", resource="files"))
        assert pm.check("user_1", "files", "write") is False
        assert pm.check("user_1", "files", "admin") is False

    def test_check_wrong_resource(self):
        pm = PermissionManager()
        pm.grant("user_1", Permission(name="r", level="read", resource="files"))
        assert pm.check("user_1", "network", "read") is False

    def test_check_unknown_user(self):
        pm = PermissionManager()
        assert pm.check("unknown", "files", "read") is False

    def test_level_hierarchy(self):
        """Test level hierarchy: read < write < execute < admin"""
        pm = PermissionManager()
        levels = ["read", "write", "execute", "admin"]

        for i, level in enumerate(levels):
            pm.grant(f"user_{level}", Permission(name=level, level=level, resource="test"))

        # Each level should grant itself and all below
        assert pm.check("user_read", "test", "read") is True
        assert pm.check("user_read", "test", "write") is False

        assert pm.check("user_write", "test", "read") is True
        assert pm.check("user_write", "test", "write") is True
        assert pm.check("user_write", "test", "execute") is False


# ── HookResult ──

class TestHookResult:
    def test_defaults(self):
        result = HookResult()
        assert result.allow is True
        assert result.block is False
        assert result.modified_input is None
        assert result.message == ""

    def test_custom(self):
        result = HookResult(allow=False, block=True, message="Blocked!")
        assert result.allow is False
        assert result.block is True
        assert result.message == "Blocked!"


# ── HookManager ──

class TestHookManager:
    def test_creation(self):
        hm = HookManager()
        assert hm.pre_hooks == {}
        assert hm.post_hooks == {}

    def test_register_pre(self):
        hm = HookManager()
        hook = lambda ctx: HookResult()
        hm.register_pre("tool_1", hook)
        assert "tool_1" in hm.pre_hooks
        assert len(hm.pre_hooks["tool_1"]) == 1

    def test_register_post(self):
        hm = HookManager()
        hook = lambda ctx, result: None
        hm.register_post("tool_1", hook)
        assert "tool_1" in hm.post_hooks
        assert len(hm.post_hooks["tool_1"]) == 1

    def test_register_multiple_pre_hooks(self):
        hm = HookManager()
        hm.register_pre("tool_1", lambda ctx: HookResult())
        hm.register_pre("tool_1", lambda ctx: HookResult())
        assert len(hm.pre_hooks["tool_1"]) == 2

    def test_run_pre_hooks_all_pass(self):
        hm = HookManager()
        hm.register_pre("tool_1", lambda ctx: HookResult(allow=True))
        hm.register_pre("tool_1", lambda ctx: HookResult(allow=True))

        result = hm.run_pre_hooks("tool_1", {"arg": "val"})
        assert result.allow is True
        assert result.block is False

    def test_run_pre_hooks_block(self):
        hm = HookManager()
        hm.register_pre("tool_1", lambda ctx: HookResult(allow=True))
        hm.register_pre("tool_1", lambda ctx: HookResult(block=True, message="Nope"))

        result = hm.run_pre_hooks("tool_1", {"arg": "val"})
        assert result.block is True
        assert result.message == "Nope"

    def test_run_pre_hooks_first_blocks(self):
        hm = HookManager()
        call_count = {"n": 0}

        def blocking_hook(ctx):
            return HookResult(block=True, message="Blocked")

        def counting_hook(ctx):
            call_count["n"] += 1
            return HookResult()

        hm.register_pre("tool_1", blocking_hook)
        hm.register_pre("tool_1", counting_hook)

        result = hm.run_pre_hooks("tool_1", {})
        assert result.block is True
        # Second hook should not be called
        assert call_count["n"] == 0

    def test_run_pre_hooks_no_hooks(self):
        hm = HookManager()
        result = hm.run_pre_hooks("unknown_tool", {})
        assert result.allow is True
        assert result.block is False

    def test_run_post_hooks(self):
        hm = HookManager()
        received = []

        hm.register_post("tool_1", lambda ctx, result: received.append(result))
        hm.run_post_hooks("tool_1", {"arg": "val"}, "tool_result")
        assert received == ["tool_result"]

    def test_run_post_hooks_multiple(self):
        hm = HookManager()
        results = []

        hm.register_post("tool_1", lambda ctx, result: results.append(f"a:{result}"))
        hm.register_post("tool_1", lambda ctx, result: results.append(f"b:{result}"))

        hm.run_post_hooks("tool_1", {}, "result")
        assert results == ["a:result", "b:result"]

    def test_run_post_hooks_no_hooks(self):
        hm = HookManager()
        # Should not raise
        hm.run_post_hooks("unknown_tool", {}, "result")


# ── SecurityGuard ──

class TestSecurityGuard:
    def test_creation(self):
        guard = SecurityGuard()
        assert guard.permissions is not None
        assert guard.hooks is not None
        assert guard.blocked_patterns == []

    def test_layer1_permission_granted(self):
        guard = SecurityGuard()
        guard.permissions.grant("user_1", Permission(name="r", level="read", resource="files"))
        assert guard.check_layer1_permission("user_1", "files", "read") is True

    def test_layer1_permission_denied(self):
        guard = SecurityGuard()
        assert guard.check_layer1_permission("user_1", "files", "write") is False

    def test_layer2_hook_allows(self):
        guard = SecurityGuard()
        allowed, msg = guard.check_layer2_hook("tool_1", {"arg": "val"})
        assert allowed is True
        assert msg == ""

    def test_layer2_hook_blocks(self):
        guard = SecurityGuard()
        guard.hooks.register_pre("tool_1", lambda ctx: HookResult(block=True, message="Dangerous"))
        allowed, msg = guard.check_layer2_hook("tool_1", {"arg": "val"})
        assert allowed is False
        assert msg == "Dangerous"

    def test_layer3_pattern_allows(self):
        guard = SecurityGuard()
        assert guard.check_layer3_pattern("normal input") is True

    def test_layer3_pattern_blocks(self):
        guard = SecurityGuard()
        guard.blocked_patterns = ["rm -rf", "DROP TABLE"]
        assert guard.check_layer3_pattern("rm -rf /") is False
        assert guard.check_layer3_pattern("DROP TABLE users") is False

    def test_layer3_pattern_partial_match(self):
        guard = SecurityGuard()
        guard.blocked_patterns = ["dangerous"]
        assert guard.check_layer3_pattern("this is dangerous code") is False
        assert guard.check_layer3_pattern("this is safe code") is True

    def test_three_layers_combined(self):
        guard = SecurityGuard()
        guard.permissions.grant("user_1", Permission(name="admin", level="admin", resource="system"))
        guard.blocked_patterns = ["malicious"]

        # Layer 1 passes
        assert guard.check_layer1_permission("user_1", "system", "admin") is True
        # Layer 2 passes (no hooks)
        allowed, _ = guard.check_layer2_hook("tool", {})
        assert allowed is True
        # Layer 3 blocks
        assert guard.check_layer3_pattern("malicious payload") is False
