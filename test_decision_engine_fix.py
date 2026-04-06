"""Test the fixed DecisionEngine.decide() implementation"""

from loom.execution.decision import DecisionEngine
from loom.types import Dashboard, EventSurface, KnowledgeSurface, LoopState


def test_decision_engine():
    """Test that DecisionEngine makes intelligent decisions based on Dashboard"""

    engine = DecisionEngine()

    print("=" * 70)
    print("DecisionEngine.decide() Test")
    print("=" * 70)

    # Test 1: Physical constraint - high rho
    print("\n1. Test: High context pressure (ρ >= 1.0)")
    result = engine.decide(context_rho=1.2, depth=1, max_depth=5, dashboard=None)
    print(f"   Decision: {result.state.value}")
    print(f"   Reason: {result.reason}")
    assert result.state == LoopState.RENEW, "Should trigger RENEW when rho >= 1.0"
    print("   ✅ Correct: RENEW triggered")

    # Test 2: Depth constraint
    print("\n2. Test: Maximum depth reached")
    result = engine.decide(context_rho=0.5, depth=5, max_depth=5, dashboard=None)
    print(f"   Decision: {result.state.value}")
    print(f"   Reason: {result.reason}")
    assert result.state == LoopState.DECOMPOSE, "Should trigger DECOMPOSE at max depth"
    print("   ✅ Correct: DECOMPOSE triggered")

    # Test 3: Interrupt requested
    print("\n3. Test: Interrupt requested with active risks")
    dashboard = Dashboard()
    dashboard.interrupt_requested = True
    dashboard.event_surface.active_risks.append({
        "event_id": "risk_001",
        "summary": "Critical system error",
        "urgency": "high"
    })
    result = engine.decide(context_rho=0.3, depth=1, max_depth=5, dashboard=dashboard)
    print(f"   Decision: {result.state.value}")
    print(f"   Reason: {result.reason}")
    assert result.state == LoopState.REASON, "Should continue with REASON to address risks"
    assert "active risks" in result.reason.lower(), "Reason should mention active risks"
    print("   ✅ Correct: REASON with risk awareness")

    # Test 4: Goal completed
    print("\n4. Test: Goal marked as completed")
    dashboard = Dashboard()
    dashboard.goal_progress = "completed"
    result = engine.decide(context_rho=0.3, depth=1, max_depth=5, dashboard=dashboard)
    print(f"   Decision: {result.state.value}")
    print(f"   Reason: {result.reason}")
    assert result.state == LoopState.GOAL_REACHED, "Should recognize goal completion"
    print("   ✅ Correct: GOAL_REACHED")

    # Test 5: High error count (critical)
    print("\n5. Test: Critical error count (>= 5)")
    dashboard = Dashboard()
    dashboard.error_count = 6
    result = engine.decide(context_rho=0.3, depth=1, max_depth=5, dashboard=dashboard)
    print(f"   Decision: {result.state.value}")
    print(f"   Reason: {result.reason}")
    assert result.state == LoopState.DECOMPOSE, "Should suggest decomposition at high error count"
    assert "error count" in result.reason.lower(), "Reason should mention error count"
    print("   ✅ Correct: DECOMPOSE due to errors")

    # Test 6: Elevated error count (warning)
    print("\n6. Test: Elevated error count (3-4)")
    dashboard = Dashboard()
    dashboard.error_count = 3
    result = engine.decide(context_rho=0.3, depth=1, max_depth=5, dashboard=dashboard)
    print(f"   Decision: {result.state.value}")
    print(f"   Reason: {result.reason}")
    assert result.state == LoopState.REASON, "Should continue but with awareness"
    assert "error count" in result.reason.lower(), "Reason should mention error count"
    print("   ✅ Correct: REASON with error awareness")

    # Test 7: Many pending events
    print("\n7. Test: Multiple pending events")
    dashboard = Dashboard()
    dashboard.event_surface.pending_events = [
        {"event_id": "evt_001", "summary": "Event 1"},
        {"event_id": "evt_002", "summary": "Event 2"},
        {"event_id": "evt_003", "summary": "Event 3"},
    ]
    result = engine.decide(context_rho=0.3, depth=1, max_depth=5, dashboard=dashboard)
    print(f"   Decision: {result.state.value}")
    print(f"   Reason: {result.reason}")
    assert result.state == LoopState.REASON, "Should continue to address events"
    assert "pending events" in result.reason.lower(), "Reason should mention pending events"
    print("   ✅ Correct: REASON to address events")

    # Test 8: High context pressure (warning)
    print("\n8. Test: High context pressure (0.8 <= ρ < 1.0)")
    dashboard = Dashboard()
    result = engine.decide(context_rho=0.85, depth=1, max_depth=5, dashboard=dashboard)
    print(f"   Decision: {result.state.value}")
    print(f"   Reason: {result.reason}")
    assert result.state == LoopState.REASON, "Should continue with awareness"
    assert "context pressure" in result.reason.lower() or "ρ" in result.reason, "Reason should mention pressure"
    print("   ✅ Correct: REASON with pressure awareness")

    # Test 9: Normal operation
    print("\n9. Test: Normal operation (no issues)")
    dashboard = Dashboard()
    dashboard.rho = 0.3
    dashboard.error_count = 0
    dashboard.goal_progress = "in_progress"
    result = engine.decide(context_rho=0.3, depth=1, max_depth=5, dashboard=dashboard)
    print(f"   Decision: {result.state.value}")
    print(f"   Reason: {result.reason}")
    assert result.state == LoopState.REASON, "Should continue normally"
    print("   ✅ Correct: REASON (normal operation)")

    # Test 10: No dashboard (fallback)
    print("\n10. Test: No dashboard provided (fallback)")
    result = engine.decide(context_rho=0.3, depth=1, max_depth=5, dashboard=None)
    print(f"   Decision: {result.state.value}")
    print(f"   Reason: {result.reason}")
    assert result.state == LoopState.REASON, "Should continue with simple loop"
    print("   ✅ Correct: REASON (fallback mode)")

    print("\n" + "=" * 70)
    print("Summary:")
    print("=" * 70)
    print("✅ All 10 decision scenarios tested successfully!")
    print("\nDecisionEngine now makes intelligent decisions based on:")
    print("  • Physical constraints (ρ, depth)")
    print("  • Interrupt requests and active risks")
    print("  • Goal completion status")
    print("  • Error thresholds")
    print("  • Pending events")
    print("  • Context pressure warnings")
    print("\n" + "=" * 70)

    return True


if __name__ == "__main__":
    success = test_decision_engine()
    exit(0 if success else 1)
