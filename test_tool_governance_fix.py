"""Test the enhanced ToolGovernance with fine-grained parameter-level control"""

from loom.tools.governance import (
    ToolGovernance,
    GovernanceConfig,
    ToolPolicy,
    ParameterConstraint,
)
from loom.tools.schema import ToolDefinition, ToolParameter


def test_tool_governance():
    """Test that ToolGovernance supports fine-grained parameter-level control"""

    print("=" * 70)
    print("ToolGovernance Fine-Grained Control Test")
    print("=" * 70)

    # Test 1: Basic tool-level permission (existing functionality)
    print("\n1. Test: Basic tool-level permission")
    config = GovernanceConfig(
        allow_tools={"bash", "python"},
        deny_tools={"rm"},
    )
    governance = ToolGovernance(config)

    ok, reason = governance.check_permission("bash")
    assert ok, "bash should be allowed"
    print("   ✅ Allowed tool works")

    ok, reason = governance.check_permission("rm")
    assert not ok, "rm should be denied"
    assert "denied" in reason.lower()
    print("   ✅ Denied tool blocked")

    ok, reason = governance.check_permission("unknown")
    assert not ok, "unknown tool should be denied (not in allowlist)"
    print("   ✅ Unknown tool blocked")

    # Test 2: Parameter constraint - regex validation
    print("\n2. Test: Parameter constraint - regex validation")
    config = GovernanceConfig(
        tool_policies={
            "bash": ToolPolicy(
                tool_name="bash",
                parameter_constraints=[
                    ParameterConstraint(
                        parameter_name="command",
                        constraint_type="regex",
                        constraint_value=r"^(ls|pwd|echo).*",
                        error_message="Only ls, pwd, echo commands allowed"
                    )
                ]
            )
        }
    )
    governance = ToolGovernance(config)

    # Valid command
    ok, reason = governance.check_permission("bash", None, {"command": "ls -la"})
    assert ok, "ls command should be allowed"
    print("   ✅ Valid regex pattern allowed")

    # Invalid command
    ok, reason = governance.check_permission("bash", None, {"command": "rm -rf /"})
    assert not ok, "rm command should be denied"
    assert "ls, pwd, echo" in reason
    print(f"   ✅ Invalid regex pattern blocked: {reason}")

    # Test 3: Parameter constraint - range validation
    print("\n3. Test: Parameter constraint - range validation")
    config = GovernanceConfig(
        tool_policies={
            "api_call": ToolPolicy(
                tool_name="api_call",
                parameter_constraints=[
                    ParameterConstraint(
                        parameter_name="timeout",
                        constraint_type="range",
                        constraint_value=(1, 30),
                        error_message="Timeout must be between 1 and 30 seconds"
                    )
                ]
            )
        }
    )
    governance = ToolGovernance(config)

    # Valid range
    ok, reason = governance.check_permission("api_call", None, {"timeout": 10})
    assert ok, "timeout=10 should be allowed"
    print("   ✅ Valid range allowed")

    # Out of range
    ok, reason = governance.check_permission("api_call", None, {"timeout": 100})
    assert not ok, "timeout=100 should be denied"
    assert "between 1 and 30" in reason
    print(f"   ✅ Out of range blocked: {reason}")

    # Test 4: Parameter constraint - enum validation
    print("\n4. Test: Parameter constraint - enum validation")
    config = GovernanceConfig(
        tool_policies={
            "deploy": ToolPolicy(
                tool_name="deploy",
                parameter_constraints=[
                    ParameterConstraint(
                        parameter_name="environment",
                        constraint_type="enum",
                        constraint_value={"dev", "staging"},
                        error_message="Can only deploy to dev or staging"
                    )
                ]
            )
        }
    )
    governance = ToolGovernance(config)

    # Valid enum
    ok, reason = governance.check_permission("deploy", None, {"environment": "dev"})
    assert ok, "environment=dev should be allowed"
    print("   ✅ Valid enum value allowed")

    # Invalid enum
    ok, reason = governance.check_permission("deploy", None, {"environment": "production"})
    assert not ok, "environment=production should be denied"
    assert "dev or staging" in reason
    print(f"   ✅ Invalid enum value blocked: {reason}")

    # Test 5: Parameter constraint - custom validator
    print("\n5. Test: Parameter constraint - custom validator")

    def validate_safe_path(path: str) -> tuple[bool, str]:
        """Custom validator: no parent directory references"""
        if ".." in path:
            return False, "Path cannot contain '..'"
        if path.startswith("/"):
            return False, "Absolute paths not allowed"
        return True, ""

    config = GovernanceConfig(
        tool_policies={
            "read_file": ToolPolicy(
                tool_name="read_file",
                parameter_constraints=[
                    ParameterConstraint(
                        parameter_name="path",
                        constraint_type="custom",
                        constraint_value=validate_safe_path,
                    )
                ]
            )
        }
    )
    governance = ToolGovernance(config)

    # Valid path
    ok, reason = governance.check_permission("read_file", None, {"path": "data/file.txt"})
    assert ok, "relative path should be allowed"
    print("   ✅ Valid custom validation passed")

    # Invalid path with ..
    ok, reason = governance.check_permission("read_file", None, {"path": "../etc/passwd"})
    assert not ok, "path with .. should be denied"
    assert ".." in reason
    print(f"   ✅ Invalid custom validation blocked: {reason}")

    # Invalid absolute path
    ok, reason = governance.check_permission("read_file", None, {"path": "/etc/passwd"})
    assert not ok, "absolute path should be denied"
    assert "Absolute" in reason
    print(f"   ✅ Absolute path blocked: {reason}")

    # Test 6: Context-aware restrictions
    print("\n6. Test: Context-aware restrictions")
    config = GovernanceConfig(
        current_context="development",
        tool_policies={
            "deploy": ToolPolicy(
                tool_name="deploy",
                allowed_contexts={"production", "staging"}
            )
        }
    )
    governance = ToolGovernance(config)

    # Not allowed in development context
    ok, reason = governance.check_permission("deploy", None, {})
    assert not ok, "deploy should not be allowed in development context"
    assert "development" in reason
    print(f"   ✅ Context restriction works: {reason}")

    # Change context
    governance.set_context("production")
    ok, reason = governance.check_permission("deploy", None, {})
    assert ok, "deploy should be allowed in production context"
    print("   ✅ Context change works")

    # Test 7: Tool-specific rate limits
    print("\n7. Test: Tool-specific rate limits")
    config = GovernanceConfig(
        max_calls_per_minute=10,
        tool_policies={
            "expensive_api": ToolPolicy(
                tool_name="expensive_api",
                max_calls_per_minute=2  # Override global limit
            )
        }
    )
    governance = ToolGovernance(config)

    # First call - should pass
    ok, reason = governance.check_rate_limit("expensive_api")
    assert ok, "First call should pass"
    governance.record_call("expensive_api")
    print("   ✅ First call allowed")

    # Second call - should pass
    ok, reason = governance.check_rate_limit("expensive_api")
    assert ok, "Second call should pass"
    governance.record_call("expensive_api")
    print("   ✅ Second call allowed")

    # Third call - should fail (limit is 2)
    ok, reason = governance.check_rate_limit("expensive_api")
    assert not ok, "Third call should fail"
    assert "2/2" in reason or "exceeded" in reason.lower()
    print(f"   ✅ Tool-specific rate limit works: {reason}")

    # Test 8: Custom policy function
    print("\n8. Test: Custom policy function")

    def custom_bash_policy(tool_name: str, arguments: dict, runtime_context) -> tuple[bool, str]:
        """Custom policy: deny dangerous commands"""
        command = arguments.get("command", "")
        dangerous = ["rm -rf", "dd if=", "mkfs", "> /dev/"]
        for pattern in dangerous:
            if pattern in command:
                return False, f"Dangerous command pattern detected: {pattern}"
        return True, ""

    config = GovernanceConfig(
        tool_policies={
            "bash": ToolPolicy(
                tool_name="bash",
                custom_policy=custom_bash_policy
            )
        }
    )
    governance = ToolGovernance(config)

    # Safe command
    ok, reason = governance.check_permission("bash", None, {"command": "ls -la"})
    assert ok, "Safe command should be allowed"
    print("   ✅ Safe command passed custom policy")

    # Dangerous command
    ok, reason = governance.check_permission("bash", None, {"command": "rm -rf /"})
    assert not ok, "Dangerous command should be denied"
    assert "rm -rf" in reason
    print(f"   ✅ Dangerous command blocked by custom policy: {reason}")

    # Test 9: Global context policy
    print("\n9. Test: Global context policy")

    def global_context_policy(tool_name: str, context: str, arguments: dict, runtime_context) -> tuple[bool, str]:
        """Global policy: restrict destructive operations in production"""
        if context == "production" and tool_name in {"bash", "python"}:
            command = arguments.get("command", "") or arguments.get("code", "")
            if any(word in command for word in ["delete", "drop", "truncate"]):
                return False, f"Destructive operations not allowed in production"
        return True, ""

    config = GovernanceConfig(
        current_context="production",
        context_policy=global_context_policy
    )
    governance = ToolGovernance(config)

    # Safe command in production
    ok, reason = governance.check_permission("bash", None, {"command": "ls"})
    assert ok, "Safe command should be allowed in production"
    print("   ✅ Safe command in production allowed")

    # Destructive command in production
    ok, reason = governance.check_permission("bash", None, {"command": "delete from users"})
    assert not ok, "Destructive command should be denied in production"
    assert "production" in reason
    print(f"   ✅ Destructive command in production blocked: {reason}")

    # Test 10: Multiple constraints on same tool
    print("\n10. Test: Multiple constraints on same tool")
    config = GovernanceConfig(
        tool_policies={
            "api_call": ToolPolicy(
                tool_name="api_call",
                parameter_constraints=[
                    ParameterConstraint(
                        parameter_name="url",
                        constraint_type="regex",
                        constraint_value=r"^https://.*",
                        error_message="Only HTTPS URLs allowed"
                    ),
                    ParameterConstraint(
                        parameter_name="timeout",
                        constraint_type="range",
                        constraint_value=(1, 30),
                    ),
                    ParameterConstraint(
                        parameter_name="method",
                        constraint_type="enum",
                        constraint_value={"GET", "POST"},
                    )
                ],
                max_calls_per_minute=5
            )
        }
    )
    governance = ToolGovernance(config)

    # All constraints satisfied
    ok, reason = governance.check_permission("api_call", None, {
        "url": "https://api.example.com",
        "timeout": 10,
        "method": "GET"
    })
    assert ok, "All constraints satisfied should be allowed"
    print("   ✅ Multiple constraints all satisfied")

    # URL constraint violated
    ok, reason = governance.check_permission("api_call", None, {
        "url": "http://api.example.com",  # HTTP not HTTPS
        "timeout": 10,
        "method": "GET"
    })
    assert not ok, "HTTP URL should be denied"
    assert "HTTPS" in reason
    print(f"   ✅ URL constraint violation detected: {reason}")

    # Method constraint violated
    ok, reason = governance.check_permission("api_call", None, {
        "url": "https://api.example.com",
        "timeout": 10,
        "method": "DELETE"  # Not in enum
    })
    assert not ok, "DELETE method should be denied"
    assert "GET" in reason or "POST" in reason
    print(f"   ✅ Method constraint violation detected: {reason}")

    # Test 11: Runtime context integration
    print("\n11. Test: Runtime context integration")

    class MockDashboard:
        def __init__(self, error_count: int):
            self.error_count = error_count

    def context_aware_policy(tool_name: str, context: str, arguments: dict, runtime_context) -> tuple[bool, str]:
        """Policy that checks runtime state"""
        if runtime_context and hasattr(runtime_context, 'error_count'):
            if runtime_context.error_count > 3:
                return False, f"Too many errors ({runtime_context.error_count}), tool execution suspended"
        return True, ""

    config = GovernanceConfig(context_policy=context_aware_policy)

    # Low error count - should pass
    dashboard = MockDashboard(error_count=2)
    governance = ToolGovernance(config, runtime_context=dashboard)
    ok, reason = governance.check_permission("bash", None, {"command": "ls"})
    assert ok, "Should be allowed with low error count"
    print("   ✅ Runtime context check passed (low errors)")

    # High error count - should fail
    dashboard = MockDashboard(error_count=5)
    governance.update_runtime_context(dashboard)
    ok, reason = governance.check_permission("bash", None, {"command": "ls"})
    assert not ok, "Should be denied with high error count"
    assert "Too many errors" in reason
    print(f"   ✅ Runtime context check blocked: {reason}")

    # Test 12: Rate limit reset
    print("\n12. Test: Rate limit reset")
    config = GovernanceConfig(max_calls_per_minute=2)
    governance = ToolGovernance(config)

    # Use up rate limit
    governance.record_call("test_tool")
    governance.record_call("test_tool")
    ok, reason = governance.check_rate_limit("test_tool")
    assert not ok, "Should hit rate limit"
    print("   ✅ Rate limit reached")

    # Reset and try again
    governance.reset_rate_limits()
    ok, reason = governance.check_rate_limit("test_tool")
    assert ok, "Should be allowed after reset"
    print("   ✅ Rate limit reset works")

    print("\n" + "=" * 70)
    print("Summary:")
    print("=" * 70)
    print("✅ All 12 tests passed!")
    print("\nToolGovernance now supports:")
    print("  • Basic tool-level permissions (allow/deny lists)")
    print("  • Parameter-level regex validation")
    print("  • Parameter-level range validation")
    print("  • Parameter-level enum validation")
    print("  • Parameter-level custom validators")
    print("  • Context-aware restrictions")
    print("  • Tool-specific rate limits")
    print("  • Custom policy functions per tool")
    print("  • Global context-aware policies")
    print("  • Multiple constraints per tool")
    print("  • Runtime context integration (Dashboard, Agent state)")
    print("  • Rate limit reset mechanism")
    print("\n" + "=" * 70)

    return True


if __name__ == "__main__":
    success = test_tool_governance()
    exit(0 if success else 1)
