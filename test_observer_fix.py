"""Test the enhanced Observer with real observation and recording"""

from datetime import datetime
import time

from loom.execution.observer import Observer, ToolObservation, ObservationHistory


def test_observer():
    """Test that Observer supports real observation and recording"""

    print("=" * 70)
    print("Observer Enhancement Test")
    print("=" * 70)

    # Test 1: Basic tool observation
    print("\n1. Test: Basic tool observation")
    observer = Observer()

    observer.start_observation("bash", {"command": "ls"})
    time.sleep(0.01)  # Simulate execution time
    msg = observer.observe_tool_result("bash", "file1.txt\nfile2.txt", {"command": "ls"})

    assert msg.role == "tool", "Should return tool message"
    assert msg.name == "bash", "Should have tool name"
    assert "file1.txt" in msg.content, "Should have result content"
    assert len(observer.history.tool_observations) == 1, "Should record observation"
    assert observer.history.success_count == 1, "Should count success"
    print("   ✅ Basic tool observation works")

    # Test 2: Error observation
    print("\n2. Test: Error observation")
    observer = Observer()

    msg = observer.observe_error("Command failed", "bash", {"command": "invalid"})

    assert msg.role == "system", "Should return system message"
    assert "[Error]" in msg.content, "Should have error prefix"
    assert observer.history.error_count == 1, "Should count error"
    assert len(observer.history.tool_observations) == 1, "Should record error observation"
    print("   ✅ Error observation works")

    # Test 3: Duration tracking
    print("\n3. Test: Duration tracking")
    observer = Observer()

    observer.start_observation("api_call", {"url": "https://example.com"})
    time.sleep(0.02)  # Simulate 20ms execution
    observer.observe_tool_result("api_call", "Success", {"url": "https://example.com"})

    obs = observer.history.tool_observations[0]
    assert obs.duration_ms > 0, "Should track duration"
    assert obs.duration_ms >= 15, f"Duration should be >= 15ms, got {obs.duration_ms}"
    print(f"   ✅ Duration tracking works ({obs.duration_ms:.2f}ms)")

    # Test 4: Multiple observations
    print("\n4. Test: Multiple observations")
    observer = Observer()

    for i in range(5):
        observer.start_observation("tool", {"arg": i})
        observer.observe_tool_result("tool", f"result_{i}", {"arg": i})

    assert len(observer.history.tool_observations) == 5, "Should record all observations"
    assert observer.history.success_count == 5, "Should count all successes"
    print("   ✅ Multiple observations recorded")

    # Test 5: Recent observations
    print("\n5. Test: Recent observations")
    observer = Observer()

    for i in range(10):
        observer.observe_tool_result("tool", f"result_{i}")

    recent = observer.get_recent_observations(3)
    assert len(recent) == 3, "Should return 3 recent observations"
    assert recent[-1].result == "result_9", "Should return most recent"
    assert recent[0].result == "result_7", "Should return in order"
    print("   ✅ Recent observations retrieval works")

    # Test 6: Tool statistics
    print("\n6. Test: Tool statistics")
    observer = Observer()

    # Tool A: 3 successes
    for i in range(3):
        observer.start_observation("tool_a", {})
        time.sleep(0.01)
        observer.observe_tool_result("tool_a", f"result_{i}", {})

    # Tool B: 2 successes, 1 error
    for i in range(2):
        observer.observe_tool_result("tool_b", f"result_{i}", {})
    observer.observe_error("Error", "tool_b", {})

    stats_a = observer.get_tool_statistics("tool_a")
    assert stats_a["count"] == 3, "Should count tool_a observations"
    assert stats_a["success_count"] == 3, "Should count tool_a successes"
    assert stats_a["error_count"] == 0, "Should count tool_a errors"
    print(f"   ✅ Tool A statistics: {stats_a['count']} calls, {stats_a['success_count']} success")

    stats_b = observer.get_tool_statistics("tool_b")
    assert stats_b["count"] == 3, "Should count tool_b observations"
    assert stats_b["success_count"] == 2, "Should count tool_b successes"
    assert stats_b["error_count"] == 1, "Should count tool_b errors"
    print(f"   ✅ Tool B statistics: {stats_b['count']} calls, {stats_b['error_count']} errors")

    # Test 7: Error rate calculation
    print("\n7. Test: Error rate calculation")
    observer = Observer()

    # 7 successes, 3 errors
    for i in range(7):
        observer.observe_tool_result("tool", f"result_{i}")
    for i in range(3):
        observer.observe_error(f"error_{i}", "tool")

    error_rate = observer.get_error_rate()
    assert error_rate == 0.3, f"Error rate should be 0.3, got {error_rate}"
    print(f"   ✅ Error rate calculation works ({error_rate:.1%})")

    # Test 8: Summary
    print("\n8. Test: Summary")
    observer = Observer()

    for i in range(5):
        observer.start_observation("tool", {})
        time.sleep(0.01)
        observer.observe_tool_result("tool", f"result_{i}", {})
    for i in range(2):
        observer.observe_error(f"error_{i}", "tool")

    summary = observer.get_summary()
    assert summary["total_observations"] == 7, "Should count all observations"
    assert summary["success_count"] == 5, "Should count successes"
    assert summary["error_count"] == 2, "Should count errors"
    assert summary["error_rate"] > 0, "Should calculate error rate"
    assert summary["total_duration_ms"] > 0, "Should track total duration"
    print(f"   ✅ Summary works: {summary['total_observations']} observations, "
          f"{summary['error_rate']:.1%} error rate")

    # Test 9: History limit
    print("\n9. Test: History limit")
    observer = Observer(max_history=5)

    for i in range(10):
        observer.observe_tool_result("tool", f"result_{i}")

    assert len(observer.history.tool_observations) == 5, "Should limit history to 5"
    assert observer.history.tool_observations[0].result == "result_5", "Should keep recent"
    assert observer.history.tool_observations[-1].result == "result_9", "Should keep most recent"
    print("   ✅ History limit works (kept 5 most recent)")

    # Test 10: Clear history
    print("\n10. Test: Clear history")
    observer = Observer()

    for i in range(5):
        observer.observe_tool_result("tool", f"result_{i}")
    observer.observe_error("error", "tool")

    observer.clear_history()

    assert len(observer.history.tool_observations) == 0, "Should clear observations"
    assert observer.history.success_count == 0, "Should reset success count"
    assert observer.history.error_count == 0, "Should reset error count"
    print("   ✅ Clear history works")

    # Test 11: Metadata recording
    print("\n11. Test: Metadata recording")
    observer = Observer()

    metadata = {"user": "test", "priority": "high"}
    observer.observe_tool_result("tool", "result", {"arg": "value"}, metadata)

    obs = observer.history.tool_observations[0]
    assert obs.metadata == metadata, "Should record metadata"
    assert obs.arguments == {"arg": "value"}, "Should record arguments"
    print("   ✅ Metadata recording works")

    # Test 12: Timestamp recording
    print("\n12. Test: Timestamp recording")
    observer = Observer()

    before = datetime.now()
    observer.observe_tool_result("tool", "result")
    after = datetime.now()

    obs = observer.history.tool_observations[0]
    assert before <= obs.timestamp <= after, "Should record timestamp"
    print(f"   ✅ Timestamp recording works ({obs.timestamp.isoformat()})")

    print("\n" + "=" * 70)
    print("Summary:")
    print("=" * 70)
    print("✅ All 12 tests passed!")
    print("\nObserver now supports:")
    print("  • Real observation recording")
    print("  • Duration tracking")
    print("  • Success/error counting")
    print("  • Tool-specific statistics")
    print("  • Error rate calculation")
    print("  • Recent observations retrieval")
    print("  • Observation summary")
    print("  • History limit management")
    print("  • History clearing")
    print("  • Metadata recording")
    print("  • Timestamp recording")
    print("  • Arguments recording")
    print("\n" + "=" * 70)

    return True


if __name__ == "__main__":
    success = test_observer()
    exit(0 if success else 1)
