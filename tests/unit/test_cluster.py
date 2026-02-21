"""Unit tests for cluster module (manager, reward, lifecycle, planner)."""

import pytest

from loom.cluster import ClusterManager
from loom.cluster.lifecycle import LifecycleManager
from loom.cluster.planner import TaskPlanner
from loom.cluster.reward import RewardBus
from loom.config import ClusterConfig
from loom.errors import ApoptosisRejectedError
from loom.types import AgentNode, CapabilityProfile, RewardRecord, SubTask, TaskAd, TaskResult
from tests.conftest import MockLLMProvider


class TestClusterManager:
    def test_add_and_get_node(self, sample_node):
        cm = ClusterManager()
        cm.add_node(sample_node)
        assert cm.get_node(sample_node.id) is sample_node

    def test_remove_node(self, sample_node):
        cm = ClusterManager()
        cm.add_node(sample_node)
        removed = cm.remove_node(sample_node.id)
        assert removed is sample_node
        assert cm.get_node(sample_node.id) is None

    def test_compute_bid(self, sample_node, sample_task):
        cm = ClusterManager()
        bid = cm.compute_bid(sample_node, sample_task)
        assert bid.score > 0
        assert bid.agent_id == sample_node.id

    def test_select_winner_prefers_idle(self):
        cm = ClusterManager()
        busy = AgentNode(
            id="busy", capabilities=CapabilityProfile(scores={"code": 0.9}), status="busy"
        )
        idle = AgentNode(
            id="idle", capabilities=CapabilityProfile(scores={"code": 0.8}), status="idle"
        )
        cm.add_node(busy)
        cm.add_node(idle)
        winner = cm.select_winner(TaskAd(domain="code"))
        assert winner.id == "idle"

    def test_select_winner_none_when_empty(self):
        cm = ClusterManager()
        assert cm.select_winner(TaskAd(domain="code")) is None

    def test_update_load(self, sample_node):
        cm = ClusterManager()
        cm.add_node(sample_node)
        cm.update_load(sample_node.id, 0.75)
        assert sample_node.load == 0.75

    def test_find_idle(self):
        cm = ClusterManager()
        n = AgentNode(id="a", status="idle")
        cm.add_node(n)
        assert cm.find_idle() is n


class TestRewardBus:
    def test_compute_signal_success(self, sample_task):
        rb = RewardBus()
        sig = rb.compute_signal(sample_task, True, 100, 0)
        assert sig.quality == 0.7
        assert sig.reliability == 1.0

    def test_compute_signal_failure(self, sample_task):
        rb = RewardBus()
        sig = rb.compute_signal(sample_task, False, 100, 1)
        assert sig.quality == 0.0
        assert sig.reliability == 0.0

    def test_evaluate_updates_node(self, sample_node, sample_task):
        rb = RewardBus()
        reward = rb.evaluate(sample_node, sample_task, True, token_cost=100)
        assert reward > 0
        assert len(sample_node.reward_history) == 1
        assert sample_node.capabilities.total_tasks == 1

    def test_consecutive_losses(self, sample_node, sample_task):
        rb = RewardBus()
        rb.evaluate(sample_node, sample_task, False)
        rb.evaluate(sample_node, sample_task, False)
        assert sample_node.consecutive_losses == 2
        rb.evaluate(sample_node, sample_task, True)
        assert sample_node.consecutive_losses == 0


class TestLifecycleManager:
    def test_should_split(self):
        lm = LifecycleManager(ClusterConfig(mitosis_threshold=0.5, max_depth=3))
        node = AgentNode(id="n", depth=1)
        task = TaskAd(estimated_complexity=0.8)
        assert lm.should_split(task, node) is True

    def test_should_not_split_at_max_depth(self):
        lm = LifecycleManager(ClusterConfig(mitosis_threshold=0.5, max_depth=2))
        node = AgentNode(id="n", depth=2)
        assert lm.should_split(TaskAd(estimated_complexity=0.8), node) is False

    def test_check_health_healthy(self):
        import time

        node = AgentNode(
            id="h",
            last_active_at=time.time(),
            reward_history=[RewardRecord(reward=0.8, domain="code")],
        )
        lm = LifecycleManager()
        report = lm.check_health(node)
        assert report.status == "healthy"

    def test_apoptosis_rejects_busy(self):
        lm = LifecycleManager()
        cm = ClusterManager()
        n1 = AgentNode(id="a", status="busy")
        n2 = AgentNode(id="b", status="idle")
        cm.add_node(n1)
        cm.add_node(n2)
        with pytest.raises(ApoptosisRejectedError):
            lm.apoptosis(n1, cm)

    def test_merge_capabilities(self):
        lm = LifecycleManager()
        src = AgentNode(
            id="s", capabilities=CapabilityProfile(scores={"code": 0.9}, tools=["a"], total_tasks=5)
        )
        tgt = AgentNode(
            id="t", capabilities=CapabilityProfile(scores={"code": 0.5}, tools=["b"], total_tasks=5)
        )
        lm.merge_capabilities(src, tgt)
        assert tgt.capabilities.scores["code"] == pytest.approx(0.7)
        assert "a" in tgt.capabilities.tools


class TestTaskPlanner:
    async def test_decompose(self, mock_llm_json):
        planner = TaskPlanner(mock_llm_json)
        subs = await planner.decompose(TaskAd(description="build app"))
        assert len(subs) >= 1
        assert subs[0].description == "sub1"

    async def test_decompose_fallback_on_bad_json(self):
        planner = TaskPlanner(MockLLMProvider(["not json"]))
        subs = await planner.decompose(TaskAd(description="task", domain="code"))
        assert len(subs) == 1
        assert subs[0].description == "task"

    async def test_execute_dag_linear(self):
        planner = TaskPlanner(MockLLMProvider())
        subs = [
            SubTask(id="a", description="first"),
            SubTask(id="b", description="second", dependencies=["a"]),
        ]
        results = await planner.execute_dag(subs, lambda s: _fake_exec(s))
        assert len(results) == 2
        assert all(r.success for r in results)

    async def test_execute_dag_cycle_detection(self):
        planner = TaskPlanner(MockLLMProvider())
        subs = [SubTask(id="a", dependencies=["b"]), SubTask(id="b", dependencies=["a"])]
        results = await planner.execute_dag(subs, lambda s: _fake_exec(s))
        assert any(not r.success for r in results)

    async def test_aggregate(self):
        planner = TaskPlanner(MockLLMProvider(["synthesized"]))
        result = await planner.aggregate(
            TaskAd(description="task"),
            [TaskResult(task_id="a", agent_id="", content="done", success=True)],
        )
        assert result == "synthesized"


async def _fake_exec(s: SubTask) -> str:
    return f"done: {s.description}"
