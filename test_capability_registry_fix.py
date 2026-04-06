"""Test the fixed CapabilityRegistry implementation"""

from loom.capabilities.registry import CapabilityRegistry, Capability
from loom.tools.registry import ToolRegistry
from loom.context.partitions import ContextPartitions
from loom.types import Message


def test_capability_registry():
    """Test that CapabilityRegistry actually activates capabilities"""

    print("=" * 70)
    print("CapabilityRegistry Test")
    print("=" * 70)

    # Test 1: Basic registration
    print("\n1. Test: Capability registration")
    registry = CapabilityRegistry()

    cap1 = Capability(
        name="web_tools",
        description="Web browsing and search capabilities",
        tools=["WebFetch", "WebSearch"],  # Use actual tool names
        keywords=["web", "search", "fetch", "browse"]
    )

    registry.register(cap1)
    assert registry.get("web_tools") == cap1, "Should retrieve registered capability"
    assert len(registry.list_capabilities()) == 1, "Should have 1 capability"
    print("   ✅ Capability registration works")

    # Test 2: Task matching
    print("\n2. Test: Task matching by keywords")
    matched = registry.match_task("I need to search the web for information")
    assert len(matched) == 1, "Should match 1 capability"
    assert matched[0].name == "web_tools", "Should match web_tools"
    print("   ✅ Task matching works")

    # Test 3: Activate without tool_registry or context
    print("\n3. Test: Activate without tool_registry or context")
    result = registry.activate("web_tools")
    assert result is True, "Should activate successfully"
    assert "web_tools" in registry.active_capabilities, "Should be in active set"
    print("   ✅ Basic activation works")

    # Test 4: Deactivate without tool_registry or context
    print("\n4. Test: Deactivate without tool_registry or context")
    result = registry.deactivate("web_tools")
    assert result is True, "Should deactivate successfully"
    assert "web_tools" not in registry.active_capabilities, "Should not be in active set"
    print("   ✅ Basic deactivation works")

    # Test 5: Activate with tool_registry
    print("\n5. Test: Activate with tool_registry")
    tool_registry = ToolRegistry()
    initial_count = len(tool_registry.list_tools())

    result = registry.activate("web_tools", tool_registry=tool_registry)
    assert result is True, "Should activate successfully"
    assert "web_tools" in registry.active_capabilities, "Should be in active set"

    # Check if tools were registered
    final_count = len(tool_registry.list_tools())
    assert final_count >= initial_count, "Should have registered tools"

    # Check specific tools
    web_fetch = tool_registry.get("WebFetch")
    web_search = tool_registry.get("WebSearch")
    assert web_fetch is not None, "WebFetch should be registered"
    assert web_search is not None, "WebSearch should be registered"
    print(f"   ✅ Tools registered (added {final_count - initial_count} tools)")

    # Test 6: Deactivate with tool_registry
    print("\n6. Test: Deactivate with tool_registry")
    result = registry.deactivate("web_tools", tool_registry=tool_registry)
    assert result is True, "Should deactivate successfully"
    assert "web_tools" not in registry.active_capabilities, "Should not be in active set"

    # Check if tools were unregistered
    web_fetch = tool_registry.get("WebFetch")
    web_search = tool_registry.get("WebSearch")
    assert web_fetch is None, "WebFetch should be unregistered"
    assert web_search is None, "WebSearch should be unregistered"
    print("   ✅ Tools unregistered")

    # Test 7: Activate with context
    print("\n7. Test: Activate with context")
    context = ContextPartitions()
    initial_skill_count = len(context.skill)

    result = registry.activate("web_tools", context=context)
    assert result is True, "Should activate successfully"
    assert "web_tools" in registry.active_capabilities, "Should be in active set"

    # Check if skill description was added
    final_skill_count = len(context.skill)
    assert final_skill_count > initial_skill_count, "Should have added skill description"
    assert any("web_tools" in skill for skill in context.skill), "Should contain web_tools"
    print(f"   ✅ Skill description added (skills: {final_skill_count})")

    # Test 8: Deactivate with context
    print("\n8. Test: Deactivate with context")
    result = registry.deactivate("web_tools", context=context)
    assert result is True, "Should deactivate successfully"
    assert "web_tools" not in registry.active_capabilities, "Should not be in active set"

    # Check if skill description was removed
    final_skill_count = len(context.skill)
    assert final_skill_count == initial_skill_count, "Should have removed skill description"
    print("   ✅ Skill description removed")

    # Test 9: Activate with both tool_registry and context
    print("\n9. Test: Activate with both tool_registry and context")
    tool_registry = ToolRegistry()
    context = ContextPartitions()

    result = registry.activate("web_tools", tool_registry=tool_registry, context=context)
    assert result is True, "Should activate successfully"
    assert "web_tools" in registry.active_capabilities, "Should be in active set"
    assert tool_registry.get("WebFetch") is not None, "Tools should be registered"
    assert len(context.skill) > 0, "Skill description should be added"
    print("   ✅ Full activation works (tools + skill)")

    # Test 10: List active capabilities
    print("\n10. Test: List active capabilities")
    active = registry.list_active()
    assert len(active) == 1, "Should have 1 active capability"
    assert active[0].name == "web_tools", "Should be web_tools"
    print("   ✅ List active capabilities works")

    # Test 11: Activate non-existent capability
    print("\n11. Test: Activate non-existent capability")
    result = registry.activate("non_existent")
    assert result is False, "Should fail to activate non-existent capability"
    assert "non_existent" not in registry.active_capabilities, "Should not be in active set"
    print("   ✅ Non-existent capability handled correctly")

    # Test 12: Double activation
    print("\n12. Test: Double activation (idempotent)")
    registry2 = CapabilityRegistry()
    registry2.register(cap1)
    result1 = registry2.activate("web_tools")
    result2 = registry2.activate("web_tools")
    assert result1 is True, "First activation should succeed"
    assert result2 is True, "Second activation should succeed (idempotent)"
    assert len(registry2.active_capabilities) == 1, "Should still have 1 active"
    print("   ✅ Double activation is idempotent")

    print("\n" + "=" * 70)
    print("Summary:")
    print("=" * 70)
    print("✅ All 12 tests passed!")
    print("\nCapabilityRegistry now:")
    print("  • Actually activates capabilities (not just adds to set)")
    print("  • Registers tools to ToolRegistry when activated")
    print("  • Unregisters tools from ToolRegistry when deactivated")
    print("  • Injects skill descriptions to Context when activated")
    print("  • Removes skill descriptions from Context when deactivated")
    print("  • Supports activation with tool_registry only")
    print("  • Supports activation with context only")
    print("  • Supports activation with both")
    print("  • Lists active capabilities")
    print("  • Handles non-existent capabilities gracefully")
    print("  • Idempotent activation/deactivation")
    print("\n" + "=" * 70)

    return True


if __name__ == "__main__":
    success = test_capability_registry()
    exit(0 if success else 1)
