"""Test orchestration module - coordinator, planner, events, communication"""

import pytest

from loom.agent.core import Agent
from loom.orchestration.coordinator import Coordinator
from loom.orchestration.planner import TaskPlanner, Task
from loom.orchestration.events import EventBus
from loom.orchestration.communication import CommunicationProtocol
from loom.orchestration.subagent import SubAgentManager
from loom.providers.base import CompletionParams, LLMProvider
from loom.types import Event


class MockProvider(LLMProvider):
    async def complete(self, messages, params: CompletionParams = None):
        return "mock response"

    async def stream(self, messages, params: CompletionParams = None):
        yield "mock"


# ── Task (planner) ──

class TestPlannerTask:
    def test_creation(self):
        task = Task(id="t1", goal="do stuff", dependencies=[])
        assert task.id == "t1"
        assert task.goal == "do stuff"
        assert task.status == "pending"
        assert task.dependencies == []

    def test_with_dependencies(self):
        task = Task(id="t2", goal="goal", dependencies=["t1"])
        assert task.dependencies == ["t1"]


# ── TaskPlanner ──

class TestTaskPlanner:
    def test_creation(self):
        planner = TaskPlanner()
        assert planner.tasks == {}

    def test_add_task(self):
        planner = TaskPlanner()
        task = Task(id="t1", goal="goal", dependencies=[])
        planner.add_task(task)
        assert "t1" in planner.tasks
        assert planner.tasks["t1"] is task

    def test_add_multiple_tasks(self):
        planner = TaskPlanner()
        planner.add_task(Task(id="t1", goal="g1", dependencies=[]))
        planner.add_task(Task(id="t2", goal="g2", dependencies=["t1"]))
        assert len(planner.tasks) == 2

    def test_get_ready_tasks_no_deps(self):
        planner = TaskPlanner()
        planner.add_task(Task(id="t1", goal="g1", dependencies=[]))
        planner.add_task(Task(id="t2", goal="g2", dependencies=[]))

        ready = planner.get_ready_tasks()
        assert len(ready) == 2

    def test_get_ready_tasks_with_deps(self):
        planner = TaskPlanner()
        planner.add_task(Task(id="t1", goal="g1", dependencies=[]))
        planner.add_task(Task(id="t2", goal="g2", dependencies=["t1"]))

        # Only t1 is ready
        ready = planner.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "t1"

    def test_get_ready_tasks_after_completion(self):
        planner = TaskPlanner()
        t1 = Task(id="t1", goal="g1", dependencies=[])
        t2 = Task(id="t2", goal="g2", dependencies=["t1"])
        planner.add_task(t1)
        planner.add_task(t2)

        # Complete t1
        t1.status = "completed"
        ready = planner.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "t2"

    def test_get_ready_tasks_chain(self):
        planner = TaskPlanner()
        t1 = Task(id="t1", goal="g1", dependencies=[])
        t2 = Task(id="t2", goal="g2", dependencies=["t1"])
        t3 = Task(id="t3", goal="g3", dependencies=["t2"])
        planner.add_task(t1)
        planner.add_task(t2)
        planner.add_task(t3)

        # Only t1 ready
        ready = planner.get_ready_tasks()
        assert [t.id for t in ready] == ["t1"]

        t1.status = "completed"
        ready = planner.get_ready_tasks()
        assert [t.id for t in ready] == ["t2"]

        t2.status = "completed"
        ready = planner.get_ready_tasks()
        assert [t.id for t in ready] == ["t3"]

    def test_get_ready_tasks_none_ready(self):
        planner = TaskPlanner()
        planner.add_task(Task(id="t1", goal="g1", dependencies=["t_missing"]))
        ready = planner.get_ready_tasks()
        # dep not in tasks, so all deps considered done
        assert len(ready) == 1

    def test_get_ready_tasks_all_completed(self):
        planner = TaskPlanner()
        t1 = Task(id="t1", goal="g1", dependencies=[], status="completed")
        planner.add_task(t1)
        ready = planner.get_ready_tasks()
        assert len(ready) == 0

    def test_create_plan(self):
        planner = TaskPlanner()
        tasks = planner.create_plan("inspect repo -> run tests -> summarize")
        assert len(tasks) == 3
        assert tasks[0].dependencies == []
        assert tasks[1].dependencies == [tasks[0].id]
        assert tasks[2].dependencies == [tasks[1].id]

    def test_update_status_and_get_task(self):
        planner = TaskPlanner()
        [task] = planner.create_plan("inspect repo")
        planner.update_status(task.id, "completed")
        assert planner.get_task(task.id).status == "completed"
        assert planner.all_completed() is True


# ── EventBus (orchestration) ──

class TestOrchestrationEventBus:
    def test_creation(self):
        bus = EventBus()
        assert bus.delta_min == 0.1
        assert bus.published_events == []

    def test_custom_delta_min(self):
        bus = EventBus(delta_min=0.5)
        assert bus.delta_min == 0.5

    def test_publish_high_delta(self):
        bus = EventBus(delta_min=0.1)
        event = Event(
            id="e1", sender="agent_1", topic="task",
            payload={"msg": "hello"}, delta_h=0.5, priority="high"
        )
        bus.publish(event)
        assert len(bus.published_events) == 1

    def test_publish_low_delta_filtered(self):
        bus = EventBus(delta_min=0.5)
        event = Event(
            id="e2", sender="agent_1", topic="task",
            payload={"msg": "low"}, delta_h=0.1, priority="low"
        )
        bus.publish(event)
        assert len(bus.published_events) == 0

    def test_subscribe_and_notify(self):
        bus = EventBus()
        received = []
        bus.subscribe("task", lambda e: received.append(e))

        event = Event(
            id="e3", sender="agent_1", topic="task",
            payload={}, delta_h=0.3, priority="medium"
        )
        bus.publish(event)
        assert len(received) == 1
        assert received[0].id == "e3"

    def test_subscribe_different_topic(self):
        bus = EventBus()
        received = []
        bus.subscribe("other", lambda e: received.append(e))

        event = Event(
            id="e4", sender="agent_1", topic="task",
            payload={}, delta_h=0.3, priority="medium"
        )
        bus.publish(event)
        assert len(received) == 0

    def test_unsubscribe(self):
        bus = EventBus()
        received = []

        callback = lambda e: received.append(e)
        bus.subscribe("task", callback)
        bus.unsubscribe("task", callback)

        event = Event(
            id="e5", sender="agent_1", topic="task",
            payload={}, delta_h=0.3, priority="medium"
        )
        bus.publish(event)
        assert len(received) == 0

    def test_multiple_subscribers(self):
        bus = EventBus()
        r1, r2 = [], []
        bus.subscribe("task", lambda e: r1.append(e))
        bus.subscribe("task", lambda e: r2.append(e))

        event = Event(
            id="e6", sender="a", topic="task",
            payload={}, delta_h=0.3, priority="medium"
        )
        bus.publish(event)
        assert len(r1) == 1
        assert len(r2) == 1


# ── CommunicationProtocol ──

class TestCommunicationProtocol:
    def test_creation(self):
        proto = CommunicationProtocol()
        assert proto.messages == []

    def test_send(self):
        proto = CommunicationProtocol()
        event = Event(
            id="e1", sender="a", topic="test",
            payload={"data": 1}, delta_h=0.5, priority="high"
        )
        proto.send(event)
        assert len(proto.messages) == 1

    def test_receive_by_topic(self):
        proto = CommunicationProtocol()
        e1 = Event(id="e1", sender="a", topic="topic_a", payload={}, delta_h=0.5, priority="high")
        e2 = Event(id="e2", sender="b", topic="topic_b", payload={}, delta_h=0.5, priority="high")
        e3 = Event(id="e3", sender="c", topic="topic_a", payload={}, delta_h=0.5, priority="high")

        proto.send(e1)
        proto.send(e2)
        proto.send(e3)

        result = proto.receive("topic_a")
        assert len(result) == 2
        assert result[0].id == "e1"
        assert result[1].id == "e3"

    def test_receive_no_match(self):
        proto = CommunicationProtocol()
        e = Event(id="e1", sender="a", topic="x", payload={}, delta_h=0.5, priority="high")
        proto.send(e)

        result = proto.receive("y")
        assert result == []

    def test_receive_empty(self):
        proto = CommunicationProtocol()
        result = proto.receive("any")
        assert result == []


# ── Coordinator ──

class TestCoordinator:
    def test_creation(self):
        bus = EventBus()
        coord = Coordinator(bus)
        assert coord.event_bus is bus
        assert coord.agents == {}

    def test_register_agent(self):
        bus = EventBus()
        coord = Coordinator(bus)

        from unittest.mock import MagicMock
        manager = MagicMock()
        coord.register_agent("agent_1", manager)
        assert "agent_1" in coord.agents
        assert coord.agents["agent_1"] is manager

    def test_register_multiple(self):
        bus = EventBus()
        coord = Coordinator(bus)

        from unittest.mock import MagicMock
        m1, m2 = MagicMock(), MagicMock()
        coord.register_agent("a1", m1)
        coord.register_agent("a2", m2)
        assert len(coord.agents) == 2

    def test_unregister_agent(self):
        bus = EventBus()
        coord = Coordinator(bus)

        from unittest.mock import MagicMock
        manager = MagicMock()
        coord.register_agent("agent_1", manager)
        coord.unregister_agent("agent_1")
        assert "agent_1" not in coord.agents

    def test_unregister_nonexistent(self):
        bus = EventBus()
        coord = Coordinator(bus)
        # Should not raise
        coord.unregister_agent("nonexistent")

    @pytest.mark.asyncio
    async def test_execute_plan_and_aggregate(self):
        bus = EventBus()
        coord = Coordinator(bus)
        parent = Agent(MockProvider())
        manager = SubAgentManager(parent, max_depth=5)
        coord.register_agent("agent_1", manager)

        planner = TaskPlanner()
        tasks = planner.create_plan("inspect repo -> summarize findings")

        results = await coord.execute_plan("agent_1", planner)
        assert set(results.keys()) == {task.id for task in tasks}
        assert all(result.success for result in results.values())
        assert planner.all_completed() is True

        summary = coord.aggregate_results(results)
        assert tasks[0].id in summary
        assert tasks[1].id in summary
        assert len(bus.published_events) == 4


class TestSubAgentManager:
    @pytest.mark.asyncio
    async def test_spawn_many(self):
        parent = Agent(MockProvider())
        manager = SubAgentManager(parent, max_depth=5)

        results = await manager.spawn_many(["task one", "task two"], depth=0)
        assert len(results) == 2
        assert all(result.success for result in results)

    @pytest.mark.asyncio
    async def test_spawn_respects_max_depth(self):
        parent = Agent(MockProvider())
        manager = SubAgentManager(parent, max_depth=1)

        result = await manager.spawn("too deep", depth=1)
        assert result.success is False
        assert result.error == "MAX_DEPTH_EXCEEDED"
