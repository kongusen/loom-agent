"""Core mechanism feature benchmarks — behavioral verification."""

import asyncio
import time
from dataclasses import dataclass

from loom.agent.interceptor import InterceptorChain, InterceptorContext
from loom.events.bus import EventBus
from loom.memory.manager import MemoryManager
from loom.memory.sliding_window import SlidingWindow
from loom.memory.working_memory import WorkingMemory
from loom.cluster.lifecycle import LifecycleManager
from loom.cluster.reward import RewardBus
from loom.cluster import ClusterManager
from loom.skills.activator import match_trigger, match_trigger_async
from loom.types import (
    UserMessage, AssistantMessage, TextDeltaEvent, ErrorEvent,
    AgentNode, CapabilityProfile, TaskAd, RewardRecord,
    MemoryEntry, Skill, SkillTrigger,
)
from loom.config import ClusterConfig
from loom.errors import MitosisError


@dataclass
class MechanismResult:
    name: str
    passed: bool
    detail: str = ""

    def to_dict(self):
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


# ── Interceptor chain ──

async def test_interceptor_ordering():
    """Interceptors execute in registration order, mutations propagate."""
    chain = InterceptorChain()
    order = []

    class _I:
        def __init__(self, name, tag):
            self.name = name
            self._tag = tag
        async def intercept(self, ctx, nxt):
            order.append(self._tag)
            ctx.metadata[self._tag] = True
            await nxt()

    chain.use(_I("first", "A"))
    chain.use(_I("second", "B"))
    chain.use(_I("third", "C"))
    ctx = InterceptorContext(messages=[])
    await chain.run(ctx)
    passed = order == ["A", "B", "C"] and all(k in ctx.metadata for k in "ABC")
    return MechanismResult(
        name="interceptor_ordering",
        passed=passed,
        detail=f"order={order}, metadata_keys={list(ctx.metadata.keys())}",
    )


# ── EventBus ──

async def test_eventbus_pattern_matching():
    """Pattern 'tool:*' should match 'tool:call' but not 'text_delta'."""
    matched = []

    class _ToolEvt:
        type = "tool:call"

    class _TextEvt:
        type = "text_delta"

    bus = EventBus()
    async def _h(e): matched.append(e.type)
    bus.on_pattern("tool:*", _h)
    await bus.emit(_ToolEvt())
    await bus.emit(_TextEvt())
    passed = matched == ["tool:call"]
    return MechanismResult(
        name="eventbus_pattern_matching",
        passed=passed,
        detail=f"matched={matched}, expect=['tool:call']",
    )


async def test_eventbus_parent_propagation():
    """Child bus events should propagate to parent."""
    parent_events = []
    parent = EventBus(node_id="parent")
    async def _h(e): parent_events.append(getattr(e, "type", ""))
    parent.on_all(_h)
    child = parent.create_child("child")
    await child.emit(TextDeltaEvent(text="hello"))
    passed = len(parent_events) == 1 and parent_events[0] == "text_delta"
    return MechanismResult(
        name="eventbus_parent_propagation",
        passed=passed,
        detail=f"parent_events={parent_events}",
    )


# ── Memory L1→L2→L3 cascade ──

async def test_memory_cascade():
    """Messages overflowing L1 should cascade to L2, then L3."""
    mgr = MemoryManager(
        l1=SlidingWindow(token_budget=30),
        l2=WorkingMemory(token_budget=40),
    )
    # Fill L1 until overflow triggers L2/L3
    for i in range(20):
        await mgr.add_message(UserMessage(content=f"message number {i} with some content"))
    l1_count = len(mgr.l1.get_messages())
    l2_entries = await mgr.l2.retrieve()
    l3_entries = await mgr.l3.retrieve()
    passed = l1_count < 20 and (len(l2_entries) > 0 or len(l3_entries) > 0)
    return MechanismResult(
        name="memory_l1_l2_l3_cascade",
        passed=passed,
        detail=f"l1={l1_count}, l2={len(l2_entries)}, l3={len(l3_entries)}",
    )


# ── Lifecycle mitosis/apoptosis ──

def test_lifecycle_mitosis_trigger():
    """Mitosis should trigger when complexity > threshold AND depth < max."""
    lm = LifecycleManager(ClusterConfig(max_depth=3, mitosis_threshold=0.6))
    node_shallow = AgentNode(id="s", depth=1)
    node_deep = AgentNode(id="d", depth=3)
    task_complex = TaskAd(domain="code", estimated_complexity=0.8)
    task_simple = TaskAd(domain="code", estimated_complexity=0.3)
    results = {
        "shallow+complex": lm.should_split(task_complex, node_shallow),
        "shallow+simple": lm.should_split(task_simple, node_shallow),
        "deep+complex": lm.should_split(task_complex, node_deep),
    }
    passed = (results["shallow+complex"] is True
              and results["shallow+simple"] is False
              and results["deep+complex"] is False)
    return MechanismResult(
        name="lifecycle_mitosis_trigger",
        passed=passed,
        detail=str(results),
    )


def test_lifecycle_merge_capabilities():
    """Merge should combine capabilities weighted by task count."""
    lm = LifecycleManager()
    src = AgentNode(id="s", capabilities=CapabilityProfile(
        scores={"code": 0.9}, total_tasks=10, tools=["search"]))
    tgt = AgentNode(id="t", capabilities=CapabilityProfile(
        scores={"code": 0.5, "data": 0.7}, total_tasks=10, tools=["shell"]))
    lm.merge_capabilities(src, tgt)
    merged_code = tgt.capabilities.scores["code"]
    has_tools = "search" in tgt.capabilities.tools and "shell" in tgt.capabilities.tools
    passed = 0.6 < merged_code < 0.8 and has_tools
    return MechanismResult(
        name="lifecycle_merge_capabilities",
        passed=passed,
        detail=f"merged_code={merged_code:.3f}, tools={tgt.capabilities.tools}",
    )


def test_lifecycle_health_states():
    """Health check should return correct status based on node state."""
    lm = LifecycleManager(ClusterConfig(consecutive_loss_limit=6, idle_timeout=60))
    healthy = AgentNode(id="h", last_active_at=time.time(),
                        reward_history=[RewardRecord(reward=0.8, domain="code")])
    dying = AgentNode(id="d", consecutive_losses=10, last_active_at=time.time(),
                      reward_history=[RewardRecord(reward=0.1, domain="code")])
    idle = AgentNode(id="i", last_active_at=0)
    results = {
        "healthy": lm.check_health(healthy).status,
        "dying_losses": lm.check_health(dying).status,
        "dying_idle": lm.check_health(idle).status,
    }
    passed = (results["healthy"] == "healthy"
              and results["dying_losses"] == "dying"
              and results["dying_idle"] == "dying")
    return MechanismResult(
        name="lifecycle_health_states",
        passed=passed,
        detail=str(results),
    )


# ── Skill activation ──

def test_skill_trigger_keyword():
    """Keyword trigger should match when keywords present in input."""
    skill = Skill(name="py", trigger=SkillTrigger(type="keyword", keywords=["python"]), priority=0.8)
    hit = match_trigger(skill, "help with python code")
    miss = match_trigger(skill, "help with java code")
    passed = hit is not None and miss is None
    return MechanismResult(
        name="skill_trigger_keyword",
        passed=passed,
        detail=f"hit={hit is not None}, miss={miss is None}",
    )


def test_skill_trigger_pattern():
    """Pattern trigger should match regex in input."""
    skill = Skill(name="fn", trigger=SkillTrigger(type="pattern", pattern=r"\bdef\s+\w+"), priority=0.9)
    hit = match_trigger(skill, "def hello():")
    miss = match_trigger(skill, "call hello()")
    passed = hit is not None and miss is None
    return MechanismResult(
        name="skill_trigger_pattern",
        passed=passed,
        detail=f"hit={hit is not None}, miss={miss is None}",
    )


def test_reward_consecutive_loss_tracking():
    """RewardBus should track consecutive losses and reset on success."""
    rb = RewardBus()
    node = AgentNode(id="n", capabilities=CapabilityProfile(scores={"code": 0.5}))
    task = TaskAd(domain="code", token_budget=1000)
    rb.evaluate(node, task, False)
    rb.evaluate(node, task, False)
    rb.evaluate(node, task, False)
    losses_after_3 = node.consecutive_losses
    rb.evaluate(node, task, True)
    losses_after_success = node.consecutive_losses
    passed = losses_after_3 == 3 and losses_after_success == 0
    return MechanismResult(
        name="reward_consecutive_loss_tracking",
        passed=passed,
        detail=f"after_3_fails={losses_after_3}, after_success={losses_after_success}",
    )


async def run_all():
    """Run all mechanism tests."""
    return [
        await test_interceptor_ordering(),
        await test_eventbus_pattern_matching(),
        await test_eventbus_parent_propagation(),
        await test_memory_cascade(),
        test_lifecycle_mitosis_trigger(),
        test_lifecycle_merge_capabilities(),
        test_lifecycle_health_states(),
        test_skill_trigger_keyword(),
        test_skill_trigger_pattern(),
        test_reward_consecutive_loss_tracking(),
    ]
