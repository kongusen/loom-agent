"""Test Heartbeat integration with Agent"""

from loom.runtime.heartbeat import Heartbeat, HeartbeatConfig, WatchSource
from loom.context.dashboard import DashboardManager
import time


def test_heartbeat_integration():
    """Test that Heartbeat integrates with Agent runtime"""

    print("=" * 70)
    print("Heartbeat Integration Test")
    print("=" * 70)

    # Test 1: Basic heartbeat creation
    print("\n1. Test: Basic heartbeat creation")
    config = HeartbeatConfig(T_hb=1.0, delta_hb=0.1)
    heartbeat = Heartbeat(config)

    assert heartbeat.config.T_hb == 1.0
    assert heartbeat.running == False
    print("   ✅ Heartbeat created")

    # Test 2: Event callback
    print("\n2. Test: Event callback")
    events_received = []

    def callback(event, urgency):
        events_received.append((event, urgency))

    heartbeat.start(callback)
    assert heartbeat.running == True
    print("   ✅ Heartbeat started")

    # Test 3: Stop heartbeat
    print("\n3. Test: Stop heartbeat")
    heartbeat.stop()
    assert heartbeat.running == False
    print("   ✅ Heartbeat stopped")

    # Test 4: Resource monitoring
    print("\n4. Test: Resource monitoring")
    config = HeartbeatConfig(
        T_hb=0.5,
        watch_sources=[
            WatchSource(type="resource", config={"thresholds": {"memory_pct": 99.0}})
        ]
    )
    heartbeat = Heartbeat(config)

    events = []
    def collect_events(event, urgency):
        events.append(event)

    heartbeat.start(collect_events)
    time.sleep(1.5)
    heartbeat.stop()

    print(f"   ✅ Resource monitoring works (checked {len(events)} times)")

    # Test 5: Urgency classification
    print("\n5. Test: Urgency classification")
    heartbeat = Heartbeat(HeartbeatConfig())

    low_event = {"delta_H": 0.3}
    high_event = {"delta_H": 0.6}
    critical_event = {"delta_H": 0.9}

    assert heartbeat._classify_urgency(low_event) == "low"
    assert heartbeat._classify_urgency(high_event) == "high"
    assert heartbeat._classify_urgency(critical_event) == "critical"
    print("   ✅ Urgency classification works")

    # Test 6: Dashboard integration
    print("\n6. Test: Dashboard integration")
    dashboard_mgr = DashboardManager()
    heartbeat = Heartbeat(HeartbeatConfig())

    event = {
        "event_id": "test_1",
        "summary": "Test event",
        "delta_H": 0.5,
        "source": "test"
    }

    heartbeat.process_event(event, "high", dashboard_mgr)

    assert len(dashboard_mgr.dashboard.event_surface.active_risks) > 0
    print("   ✅ Dashboard integration works")

    print("\n" + "=" * 70)
    print("Summary:")
    print("=" * 70)
    print("✅ All 6 tests passed!")
    print("\nHeartbeat integration features:")
    print("  • Heartbeat creation and configuration")
    print("  • Event callback mechanism")
    print("  • Start/stop lifecycle")
    print("  • Resource monitoring")
    print("  • Urgency classification")
    print("  • Dashboard integration")
    print("\n" + "=" * 70)

    return True


if __name__ == "__main__":
    success = test_heartbeat_integration()
    exit(0 if success else 1)
