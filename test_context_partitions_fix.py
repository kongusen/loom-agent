"""Test the fixed ContextPartitions.get_all_messages() implementation"""

from loom.context.partitions import ContextPartitions
from loom.types import Message, Dashboard, EventSurface, KnowledgeSurface


def test_get_all_messages():
    """Test that get_all_messages() includes all partitions"""

    # Create partitions with data in all sections
    partitions = ContextPartitions()

    # 1. C_system
    partitions.system.append(
        Message(role="system", content="You are a helpful assistant.")
    )

    # 2. C_working (Dashboard)
    partitions.working.rho = 0.65
    partitions.working.token_budget = 150000
    partitions.working.goal_progress = "in_progress"
    partitions.working.error_count = 1
    partitions.working.depth = 2
    partitions.working.plan = [
        "Analyze the problem",
        "Generate solution",
        "Verify result"
    ]
    partitions.working.scratchpad = "Working on step 2..."
    partitions.working.event_surface.pending_events.append({
        "event_id": "evt_001",
        "summary": "File system changed",
        "urgency": "medium"
    })
    partitions.working.knowledge_surface.active_questions.append(
        "What is the best approach for this task?"
    )
    partitions.working.knowledge_surface.citations.append(
        "Documentation: API Reference v2.0"
    )

    # 3. C_memory
    partitions.memory.append(
        Message(role="system", content="Previous context: User prefers concise answers.")
    )

    # 4. C_skill
    partitions.skill.append("calculator: Perform arithmetic operations")
    partitions.skill.append("web_search: Search the web for information")

    # 5. C_history
    partitions.history.append(
        Message(role="user", content="Calculate 5 + 3")
    )
    partitions.history.append(
        Message(role="assistant", content="The result is 8.")
    )

    # Get all messages
    messages = partitions.get_all_messages()

    print("=" * 70)
    print("ContextPartitions.get_all_messages() Test")
    print("=" * 70)
    print(f"\nTotal messages: {len(messages)}")
    print("\nMessage breakdown:")

    for i, msg in enumerate(messages, 1):
        print(f"\n{i}. Role: {msg.role}")
        preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
        print(f"   Content preview: {preview}")

    print("\n" + "=" * 70)
    print("Detailed Dashboard Message:")
    print("=" * 70)

    # Find and display the dashboard message
    dashboard_msg = None
    for msg in messages:
        if "Dashboard" in msg.content and msg.role == "system":
            dashboard_msg = msg
            break

    if dashboard_msg:
        print(dashboard_msg.content)
    else:
        print("❌ Dashboard message not found!")

    print("\n" + "=" * 70)
    print("Detailed Skills Message:")
    print("=" * 70)

    # Find and display the skills message
    skills_msg = None
    for msg in messages:
        if "Available Skills" in msg.content and msg.role == "system":
            skills_msg = msg
            break

    if skills_msg:
        print(skills_msg.content)
    else:
        print("❌ Skills message not found!")

    print("\n" + "=" * 70)
    print("Verification:")
    print("=" * 70)

    # Verify all partitions are included
    checks = {
        "C_system included": any("helpful assistant" in msg.content for msg in messages),
        "C_working (Dashboard) included": any("Dashboard" in msg.content for msg in messages),
        "C_memory included": any("Previous context" in msg.content for msg in messages),
        "C_skill included": any("Available Skills" in msg.content for msg in messages),
        "C_history included": any("Calculate 5 + 3" in msg.content for msg in messages),
        "Dashboard shows rho": dashboard_msg and "0.65" in dashboard_msg.content if dashboard_msg else False,
        "Dashboard shows plan": dashboard_msg and "Current Plan" in dashboard_msg.content if dashboard_msg else False,
        "Dashboard shows events": dashboard_msg and "Pending Events" in dashboard_msg.content if dashboard_msg else False,
        "Dashboard shows questions": dashboard_msg and "Active Questions" in dashboard_msg.content if dashboard_msg else False,
        "Dashboard shows scratchpad": dashboard_msg and "Scratchpad" in dashboard_msg.content if dashboard_msg else False,
        "Skills shows calculator": skills_msg and "calculator" in skills_msg.content if skills_msg else False,
        "Skills shows web_search": skills_msg and "web_search" in skills_msg.content if skills_msg else False,
    }

    all_passed = True
    for check, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check}")
        if not result:
            all_passed = False

    print("\n" + "=" * 70)

    if all_passed:
        print("✅ All checks passed! ContextPartitions.get_all_messages() is now complete.")
    else:
        print("❌ Some checks failed. See details above.")

    return all_passed


if __name__ == "__main__":
    success = test_get_all_messages()
    exit(0 if success else 1)
