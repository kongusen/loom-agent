"""Performance benchmarks — timing core operations."""

import asyncio
import time
import statistics
from dataclasses import dataclass, field, asdict

from loom.memory.manager import MemoryManager
from loom.memory.sliding_window import SlidingWindow
from loom.memory.working_memory import WorkingMemory
from loom.events.bus import EventBus
from loom.agent.interceptor import InterceptorChain, InterceptorContext
from loom.context.orchestrator import ContextOrchestrator
from loom.knowledge.base import KnowledgeBase
from loom.knowledge.retrievers import InMemoryVectorStore
from loom.cluster.reward import RewardBus
from loom.cluster import ClusterManager
from loom.types import (
    UserMessage, AssistantMessage, MemoryEntry,
    AgentNode, CapabilityProfile, TaskAd,
    TextDeltaEvent, Document, ContextFragment,
)


@dataclass
class BenchResult:
    name: str
    iterations: int
    times_ms: list[float] = field(default_factory=list)

    @property
    def min(self): return min(self.times_ms)
    @property
    def max(self): return max(self.times_ms)
    @property
    def mean(self): return statistics.mean(self.times_ms)
    @property
    def stddev(self): return statistics.stdev(self.times_ms) if len(self.times_ms) > 1 else 0.0
    @property
    def ops_per_sec(self): return 1000 / self.mean if self.mean > 0 else float('inf')

    def to_dict(self):
        return {
            "name": self.name, "iterations": self.iterations,
            "min_ms": round(self.min, 4), "max_ms": round(self.max, 4),
            "mean_ms": round(self.mean, 4), "stddev_ms": round(self.stddev, 4),
            "ops_per_sec": round(self.ops_per_sec, 1),
        }


def _timeit(func, n=100):
    """Run sync func n times, return BenchResult."""
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        func()
        times.append((time.perf_counter() - t0) * 1000)
    return times


async def _atimeit(coro_factory, n=100):
    """Run async func n times, return times in ms."""
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        await coro_factory()
        times.append((time.perf_counter() - t0) * 1000)
    return times


# ── Mock embedding for perf tests ──

class _PerfEmbedder:
    async def embed(self, text):
        h = hash(text)
        return [(h >> i & 0xFF) / 255.0 for i in range(8)]
    async def embed_batch(self, texts):
        return [await self.embed(t) for t in texts]


# ── Individual benchmarks ──

async def bench_memory_pipeline(n=200):
    """Measure L1→L2→L3 write throughput."""
    mgr = MemoryManager(
        l1=SlidingWindow(token_budget=500),
        l2=WorkingMemory(token_budget=1000),
    )
    times = await _atimeit(
        lambda: mgr.add_message(UserMessage(content=f"msg {time.monotonic()}")), n
    )
    return BenchResult(name="memory_pipeline_write", iterations=n, times_ms=times)


async def bench_eventbus_emit(n=500):
    """Measure EventBus emit throughput with multiple subscribers."""
    bus = EventBus()
    counter = [0]
    for _ in range(5):
        async def _h(e, c=counter): c[0] += 1
        bus.on("text_delta", _h)
    evt = TextDeltaEvent(text="hello")
    times = await _atimeit(lambda: bus.emit(evt), n)
    return BenchResult(name="eventbus_emit_5sub", iterations=n, times_ms=times)


async def bench_interceptor_chain(n=200):
    """Measure interceptor chain latency with N middleware layers."""
    chain = InterceptorChain()
    for i in range(10):
        class _I:
            name = f"i{i}"
            async def intercept(self, ctx, nxt): await nxt()
        chain.use(_I())
    ctx = InterceptorContext(messages=[UserMessage(content="test")])
    times = await _atimeit(lambda: chain.run(ctx), n)
    return BenchResult(name="interceptor_chain_10", iterations=n, times_ms=times)


async def bench_context_gather(n=100):
    """Measure ContextOrchestrator gather with multiple providers."""
    orch = ContextOrchestrator()
    for i in range(3):
        class _P:
            source = f"src{i}"
            async def provide(self, q, budget):
                return [ContextFragment(source=self.source, content=f"frag {q}", tokens=10, relevance=0.8)]
        orch.register(_P())
    times = await _atimeit(lambda: orch.gather("test query", budget=5000), n)
    return BenchResult(name="context_gather_3prov", iterations=n, times_ms=times)


async def bench_hybrid_retrieval(n=50):
    """Measure hybrid retrieval (keyword + vector RRF) latency."""
    emb = _PerfEmbedder()
    vs = InMemoryVectorStore()
    kb = KnowledgeBase(embedder=emb, vector_store=vs)
    docs = [Document(id=f"d{i}", content=f"Python programming language tutorial part {i}") for i in range(20)]
    await kb.ingest(docs)
    times = await _atimeit(lambda: kb.query("Python tutorial"), n)
    return BenchResult(name="hybrid_retrieval_20docs", iterations=n, times_ms=times)


async def bench_reward_evaluate(n=500):
    """Measure RewardBus evaluate throughput."""
    rb = RewardBus()
    node = AgentNode(id="n", capabilities=CapabilityProfile(scores={"code": 0.5}))
    task = TaskAd(domain="code", description="test")
    times = _timeit(lambda: rb.evaluate(node, task, True, token_cost=100), n)
    return BenchResult(name="reward_evaluate", iterations=n, times_ms=times)


async def bench_auction(n=200):
    """Measure cluster auction with N agents."""
    cm = ClusterManager()
    for i in range(10):
        cm.add_node(AgentNode(id=f"a{i}", capabilities=CapabilityProfile(
            scores={"code": 0.3 + i * 0.05, "data": 0.5}, success_rate=0.7
        )))
    task = TaskAd(domain="code", description="test")
    times = _timeit(lambda: cm.select_winner(task), n)
    return BenchResult(name="auction_10agents", iterations=n, times_ms=times)


async def run_all():
    """Run all performance benchmarks, return list of BenchResult."""
    return [
        await bench_memory_pipeline(),
        await bench_eventbus_emit(),
        await bench_interceptor_chain(),
        await bench_context_gather(),
        await bench_hybrid_retrieval(),
        await bench_reward_evaluate(),
        await bench_auction(),
    ]
