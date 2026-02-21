"""Core logic correctness benchmarks — algorithm verification."""

from dataclasses import dataclass

from loom.cluster import ClusterManager
from loom.cluster.reward import RewardBus
from loom.context.orchestrator import ContextOrchestrator
from loom.knowledge.base import KnowledgeBase
from loom.knowledge.retrievers import InMemoryVectorStore
from loom.memory.working_memory import WorkingMemory
from loom.types import (
    AgentNode,
    CapabilityProfile,
    ContextFragment,
    Document,
    MemoryEntry,
    TaskAd,
)


@dataclass
class LogicResult:
    name: str
    passed: bool
    detail: str = ""

    def to_dict(self):
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


# ── Mock embedding for logic tests ──


class _LogicEmbedder:
    async def embed(self, text):
        h = hash(text)
        return [(h >> i & 0xFF) / 255.0 for i in range(8)]

    async def embed_batch(self, texts):
        return [await self.embed(t) for t in texts]


# ── EMA convergence ──


def test_ema_convergence():
    """After repeated successes, capability score should converge toward high value."""
    rb = RewardBus(alpha=0.3)
    node = AgentNode(id="n", capabilities=CapabilityProfile(scores={"code": 0.5}))
    task = TaskAd(domain="code", description="test", token_budget=1000)
    for _ in range(30):
        rb.evaluate(node, task, True, token_cost=100)
    score = node.capabilities.scores["code"]
    # Reward for success with cost=100/budget=1000 is ~0.82, EMA converges there
    converged = 0.75 < score < 0.90
    return LogicResult(
        name="ema_convergence",
        passed=converged,
        detail=f"score={score:.4f} after 30 successes (expect 0.75-0.90)",
    )


def test_ema_failure_decay():
    """After repeated failures, capability score should decay toward low value."""
    rb = RewardBus(alpha=0.3)
    node = AgentNode(id="n", capabilities=CapabilityProfile(scores={"code": 0.8}))
    task = TaskAd(domain="code", description="test", token_budget=1000)
    for _ in range(20):
        rb.evaluate(node, task, False, token_cost=500)
    score = node.capabilities.scores["code"]
    decayed = score < 0.4
    return LogicResult(
        name="ema_failure_decay",
        passed=decayed,
        detail=f"score={score:.4f} after 20 failures (expect <0.4)",
    )


async def test_rrf_fusion_ranking():
    """RRF should rank docs appearing in both keyword+vector higher than single-source."""
    emb = _LogicEmbedder()
    vs = InMemoryVectorStore()
    kb = KnowledgeBase(embedder=emb, vector_store=vs)
    await kb.ingest(
        [
            Document(id="d1", content="Python programming language"),
            Document(id="d2", content="Java enterprise framework"),
            Document(id="d3", content="Python data science tutorial"),
        ]
    )
    results = await kb.query("Python programming")
    ids = [r.chunk.id for r in results]
    # Python docs (d1, d3) should rank above Java doc (d2) via keyword+vector fusion
    python_ids = [i for i in ids if "d1" in i or "d3" in i]
    java_ids = [i for i in ids if "d2" in i]
    python_above_java = (
        python_ids and java_ids and ids.index(python_ids[0]) < ids.index(java_ids[0])
    )
    return LogicResult(
        name="rrf_fusion_ranking",
        passed=python_above_java and len(results) >= 2,
        detail=f"top={ids[:3]}, expect Python docs above Java",
    )


async def test_budget_allocation_proportional():
    """Higher-scored provider should get proportionally more budget."""
    orch = ContextOrchestrator(adaptive_alpha=0.3)
    budgets_seen = {}

    class _P:
        def __init__(self, src, rel):
            self.source = src
            self._rel = rel

        async def provide(self, q, budget):
            budgets_seen[self.source] = budget
            return [ContextFragment(source=self.source, content="x", tokens=5, relevance=self._rel)]

    orch.register(_P("high", 0.9))
    orch.register(_P("low", 0.1))
    # Warm up scores with a first gather
    await orch.gather("q", budget=1000)
    budgets_seen.clear()
    # Second gather uses updated scores
    await orch.gather("q", budget=1000)
    high_got_more = budgets_seen.get("high", 0) > budgets_seen.get("low", 0)
    return LogicResult(
        name="budget_allocation_proportional",
        passed=high_got_more,
        detail=f"high={budgets_seen.get('high')}, low={budgets_seen.get('low')}",
    )


def test_auction_highest_capability_wins():
    """Auction should select agent with highest capability for task domain."""
    cm = ClusterManager()
    cm.add_node(AgentNode(id="low", capabilities=CapabilityProfile(scores={"code": 0.3})))
    cm.add_node(AgentNode(id="mid", capabilities=CapabilityProfile(scores={"code": 0.6})))
    cm.add_node(AgentNode(id="high", capabilities=CapabilityProfile(scores={"code": 0.9})))
    task = TaskAd(domain="code", description="test")
    winner = cm.select_winner(task)
    passed = winner is not None and winner.id == "high"
    return LogicResult(
        name="auction_highest_wins",
        passed=passed,
        detail=f"winner={winner.id if winner else None}, expect=high",
    )


def test_auction_prefers_idle():
    """Among similar scores, auction should prefer idle agents over busy."""
    cm = ClusterManager()
    busy = AgentNode(id="busy", capabilities=CapabilityProfile(scores={"code": 0.9}))
    busy.status = "busy"
    cm.add_node(busy)
    cm.add_node(AgentNode(id="idle", capabilities=CapabilityProfile(scores={"code": 0.85})))
    winner = cm.select_winner(TaskAd(domain="code"))
    passed = winner is not None and winner.id == "idle"
    return LogicResult(
        name="auction_prefers_idle",
        passed=passed,
        detail=f"winner={winner.id if winner else None}, expect=idle",
    )


async def test_memory_eviction_order():
    """WorkingMemory should evict lowest-importance entries first."""
    wm = WorkingMemory(token_budget=50)
    await wm.store(MemoryEntry(content="high", tokens=20, importance=0.9))
    await wm.store(MemoryEntry(content="low", tokens=20, importance=0.1))
    evicted = await wm.store(MemoryEntry(content="new", tokens=20, importance=0.5))
    evicted_contents = [e.content for e in evicted]
    passed = "low" in evicted_contents and "high" not in evicted_contents
    return LogicResult(
        name="memory_eviction_order",
        passed=passed,
        detail=f"evicted={evicted_contents}, expect=['low']",
    )


def test_reward_signal_weights():
    """Reward = 0.5*quality + 0.3*efficiency + 0.2*reliability."""
    rb = RewardBus()
    task = TaskAd(domain="code", token_budget=1000)
    sig = rb.compute_signal(task, success=True, token_cost=100, error_count=0)
    reward = rb.compute_reward(sig)
    expected = 0.5 * 0.7 + 0.3 * 0.9 + 0.2 * 1.0  # 0.35 + 0.27 + 0.2 = 0.82
    passed = abs(reward - expected) < 0.01
    return LogicResult(
        name="reward_signal_weights",
        passed=passed,
        detail=f"reward={reward:.4f}, expected={expected:.4f}",
    )


async def run_all():
    """Run all logic tests, return list of LogicResult."""
    return [
        test_ema_convergence(),
        test_ema_failure_decay(),
        await test_rrf_fusion_ranking(),
        await test_budget_allocation_proportional(),
        test_auction_highest_capability_wins(),
        test_auction_prefers_idle(),
        await test_memory_eviction_order(),
        test_reward_signal_weights(),
    ]
