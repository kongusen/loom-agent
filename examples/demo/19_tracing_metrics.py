"""
19_tracing_metrics.py - Tracing 与 Metrics 可观测性

演示：
- LoomTracer 结构化追踪（嵌套 Span、SpanKind）
- InMemoryExporter / LogSpanExporter 导出器
- trace_id / span_id / parent_span_id 链路关系
- Span 属性、事件、错误记录
- LoomMetrics 指标收集（counter / gauge / histogram）
- 知识搜索专用指标（search_total / latency / hit_rate）
- 模拟完整 Agent 执行链路的追踪
"""

import asyncio
import time

from loom.observability import LoomMetrics, LoomTracer, SpanKind
from loom.observability.tracing import InMemoryExporter


async def demo_basic_tracing():
    """演示基础追踪：嵌套 Span"""
    print("=" * 60)
    print("[1] LoomTracer — 嵌套 Span 追踪")
    print("=" * 60)

    tracer = LoomTracer(agent_id="demo-agent")
    exporter = InMemoryExporter()
    tracer.add_exporter(exporter)

    # 模拟 Agent 执行链路：Agent Run → Iteration → LLM Call + Tool Execution
    with tracer.start_span(SpanKind.AGENT_RUN, "agent.run") as run_span:
        run_span.set_attribute("task", "查询产品文档")
        run_span.set_attribute("max_iterations", 3)

        # 迭代 1
        with tracer.start_span(SpanKind.AGENT_ITERATION, "iteration-1") as iter_span:
            iter_span.set_attribute("iteration", 1)

            # Context Building
            with tracer.start_span(SpanKind.CONTEXT_BUILD, "build-context") as ctx_span:
                ctx_span.set_attribute("sources", ["L1", "L2", "RAG"])
                ctx_span.set_attribute("budget_tokens", 4000)
                await asyncio.sleep(0.01)  # 模拟耗时

            # LLM 调用
            with tracer.start_span(SpanKind.LLM_CALL, "gpt-4o") as llm_span:
                llm_span.set_attribute("tokens_in", 1200)
                llm_span.set_attribute("tokens_out", 350)
                await asyncio.sleep(0.02)

            # 知识搜索（Agent 主动调用 query 工具）
            with tracer.start_span(SpanKind.KNOWLEDGE_SEARCH, "query") as search_span:
                search_span.set_attribute("query", "OAuth2.0 认证")
                search_span.set_attribute("scope", "auto")
                search_span.set_attribute("results_count", 3)
                search_span.add_event("cache_miss", {"session_id": "sess-001"})
                await asyncio.sleep(0.01)

    # 输出追踪结果
    print(f"\n  Trace ID: {tracer._trace_id}")
    print(f"  总 Span 数: {len(exporter.spans)}")
    print()

    for span in exporter.spans:
        indent = "    " if span.parent_span_id else "  "
        if span.parent_span_id and any(
            s.span_id == span.parent_span_id and s.parent_span_id for s in exporter.spans
        ):
            indent = "      "
        print(f"{indent}[{span.kind.value}] {span.name}")
        print(f"{indent}  span_id={span.span_id}  parent={span.parent_span_id or 'root'}")
        print(f"{indent}  duration={span.duration_ms:.1f}ms  status={span.status}")
        if span.attributes:
            attrs = {k: v for k, v in span.attributes.items() if k != "agent_id"}
            if attrs:
                print(f"{indent}  attrs={attrs}")
        if span.events:
            for evt in span.events:
                print(f"{indent}  event: {evt['name']} {evt.get('attributes', {})}")

    # Trace 摘要
    summary = tracer.get_trace_summary()
    print("\n  Trace 摘要:")
    print(f"    span_count={summary['span_count']}")
    print(f"    total_duration={summary['total_duration_ms']:.1f}ms")
    print(f"    spans_by_kind={summary['spans_by_kind']}")


async def demo_error_tracing():
    """演示错误追踪"""
    print("\n" + "=" * 60)
    print("[2] 错误追踪 — Span 异常捕获")
    print("=" * 60)

    tracer = LoomTracer(agent_id="demo-agent")
    exporter = InMemoryExporter()
    tracer.add_exporter(exporter)
    tracer.new_trace()

    # 模拟工具执行失败
    try:
        with tracer.start_span(SpanKind.TOOL_EXECUTION, "sandbox-exec") as span:
            span.set_attribute("tool", "python_exec")
            span.set_attribute("code_length", 150)
            raise TimeoutError("Sandbox execution timed out after 5s")
    except TimeoutError:
        pass  # 异常已被 Span 捕获

    error_span = exporter.spans[-1]
    print(f"\n  Span: {error_span.name}")
    print(f"  Status: {error_span.status}")
    print(f"  Error: {error_span.error_message}")
    print(f"  Events: {[e['name'] for e in error_span.events]}")
    if error_span.events:
        exc_event = error_span.events[0]
        print(f"  Exception type: {exc_event['attributes'].get('type')}")


async def demo_metrics_counters():
    """演示 LoomMetrics counter 指标"""
    print("\n" + "=" * 60)
    print("[3] LoomMetrics — Counter 指标")
    print("=" * 60)

    metrics = LoomMetrics(agent_id="demo-agent")

    # 模拟 Agent 运行过程中的指标累积
    for i in range(5):
        metrics.increment(LoomMetrics.ITERATIONS_TOTAL)
        metrics.increment(LoomMetrics.TOOL_CALLS_TOTAL, 2)  # 每轮调用 2 个工具
        metrics.record_tokens(input_tokens=800 + i * 100, output_tokens=200 + i * 50)

    # 模拟一次工具错误
    metrics.increment(LoomMetrics.TOOL_ERRORS_TOTAL)

    # 知识搜索指标
    metrics.increment(LoomMetrics.KNOWLEDGE_SEARCH_TOTAL, 3)

    snapshot = metrics.snapshot()
    counters = snapshot["counters"]

    print(f"\n  Agent: {snapshot['agent_id']}")
    print(f"  迭代次数: {counters.get(LoomMetrics.ITERATIONS_TOTAL, 0):.0f}")
    print(f"  工具调用: {counters.get(LoomMetrics.TOOL_CALLS_TOTAL, 0):.0f}")
    print(f"  工具错误: {counters.get(LoomMetrics.TOOL_ERRORS_TOTAL, 0):.0f}")
    print(f"  输入 tokens: {counters.get(LoomMetrics.TOKEN_INPUT, 0):.0f}")
    print(f"  输出 tokens: {counters.get(LoomMetrics.TOKEN_OUTPUT, 0):.0f}")
    print(f"  知识搜索: {counters.get(LoomMetrics.KNOWLEDGE_SEARCH_TOTAL, 0):.0f}")


async def demo_metrics_histograms():
    """演示 LoomMetrics histogram 指标（延迟分布）"""
    print("\n" + "=" * 60)
    print("[4] LoomMetrics — Histogram 指标（延迟分布）")
    print("=" * 60)

    metrics = LoomMetrics(agent_id="demo-agent")

    # 模拟 LLM 调用延迟
    llm_latencies = [120.5, 95.3, 210.8, 88.1, 150.2, 180.4, 105.7, 320.1, 140.6, 175.3]
    for lat in llm_latencies:
        metrics.observe(LoomMetrics.LLM_LATENCY, lat)

    # 模拟知识搜索延迟
    search_latencies = [32.1, 45.8, 28.3, 55.2, 38.7]
    for lat in search_latencies:
        metrics.observe(LoomMetrics.KNOWLEDGE_SEARCH_LATENCY, lat)

    # 模拟知识搜索结果数
    for count in [3, 5, 2, 4, 1]:
        metrics.observe(LoomMetrics.KNOWLEDGE_RESULTS_COUNT, count)

    snapshot = metrics.snapshot()
    histograms = snapshot["histograms"]

    print(f"\n  LLM 调用延迟 ({len(llm_latencies)} 次):")
    llm_hist = histograms.get(LoomMetrics.LLM_LATENCY, {})
    print(f"    avg={llm_hist.get('avg', 0):.1f}ms  min={llm_hist.get('min', 0):.1f}ms  max={llm_hist.get('max', 0):.1f}ms")
    print(f"    p50={llm_hist.get('p50', 0):.1f}ms  p95={llm_hist.get('p95', 0):.1f}ms  p99={llm_hist.get('p99', 0):.1f}ms")

    print(f"\n  知识搜索延迟 ({len(search_latencies)} 次):")
    search_hist = histograms.get(LoomMetrics.KNOWLEDGE_SEARCH_LATENCY, {})
    print(f"    avg={search_hist.get('avg', 0):.1f}ms  min={search_hist.get('min', 0):.1f}ms  max={search_hist.get('max', 0):.1f}ms")

    print("\n  知识搜索结果数:")
    results_hist = histograms.get(LoomMetrics.KNOWLEDGE_RESULTS_COUNT, {})
    print(f"    avg={results_hist.get('avg', 0):.1f}  min={results_hist.get('min', 0):.0f}  max={results_hist.get('max', 0):.0f}")


async def demo_metrics_gauges():
    """演示 LoomMetrics gauge 指标（实时状态）"""
    print("\n" + "=" * 60)
    print("[5] LoomMetrics — Gauge 指标（实时状态）")
    print("=" * 60)

    metrics = LoomMetrics(agent_id="demo-agent")

    # 模拟迭代过程中的预算使用率和记忆使用率变化
    iterations = [
        (1, 0.15, 0.10, 0.05),  # (iter, budget_used, l1_usage, l2_usage)
        (3, 0.35, 0.30, 0.15),
        (5, 0.55, 0.60, 0.25),
        (8, 0.72, 0.85, 0.40),
        (10, 0.88, 0.95, 0.55),
    ]

    print(f"\n  {'迭代':>4}  {'预算使用':>8}  {'L1 使用':>8}  {'L2 使用':>8}")
    print(f"  {'─'*4}  {'─'*8}  {'─'*8}  {'─'*8}")

    for iteration, budget, l1, l2 in iterations:
        metrics.set_gauge(LoomMetrics.CONTEXT_BUDGET_USED, budget)
        metrics.set_gauge(LoomMetrics.MEMORY_L1_USAGE, l1)
        metrics.set_gauge(LoomMetrics.MEMORY_L2_USAGE, l2)

        snapshot = metrics.snapshot()
        gauges = snapshot["gauges"]
        print(f"  {iteration:>4}  "
              f"{gauges[LoomMetrics.CONTEXT_BUDGET_USED]:>7.0%}  "
              f"{gauges[LoomMetrics.MEMORY_L1_USAGE]:>7.0%}  "
              f"{gauges[LoomMetrics.MEMORY_L2_USAGE]:>7.0%}")

    print("\n  Gauge 反映最新状态（非累积），适合监控资源使用率")


async def demo_full_trace_simulation():
    """模拟完整 Agent 执行链路的追踪 + 指标"""
    print("\n" + "=" * 60)
    print("[6] 完整链路模拟 — Tracing + Metrics 联动")
    print("=" * 60)

    tracer = LoomTracer(agent_id="prod-agent")
    metrics = LoomMetrics(agent_id="prod-agent")
    exporter = InMemoryExporter()
    tracer.add_exporter(exporter)

    with tracer.start_span(SpanKind.AGENT_RUN, "agent.run") as run_span:
        run_span.set_attribute("task", "帮用户排查 API 429 错误")

        for i in range(1, 4):
            metrics.increment(LoomMetrics.ITERATIONS_TOTAL)

            with tracer.start_span(SpanKind.AGENT_ITERATION, f"iter-{i}"):

                # Context building
                with tracer.start_span(SpanKind.CONTEXT_BUILD, "context"):
                    await asyncio.sleep(0.005)

                # 被动检索（context building 中的 RAG 注入）
                with tracer.start_span(SpanKind.KNOWLEDGE_RETRIEVAL, "passive-rag") as rag:
                    rag.set_attribute("source", "product_docs")
                    rag.set_attribute("results", 2)
                    await asyncio.sleep(0.005)

                # LLM 调用
                t0 = time.monotonic()
                with tracer.start_span(SpanKind.LLM_CALL, "gpt-4o") as llm:
                    llm.set_attribute("tokens_in", 1500 + i * 200)
                    llm.set_attribute("tokens_out", 300 + i * 50)
                    metrics.record_tokens(1500 + i * 200, 300 + i * 50)
                    await asyncio.sleep(0.01)
                metrics.observe(LoomMetrics.LLM_LATENCY, (time.monotonic() - t0) * 1000)

                # 第 2 轮：Agent 主动搜索
                if i == 2:
                    metrics.increment(LoomMetrics.KNOWLEDGE_SEARCH_TOTAL)
                    t0 = time.monotonic()
                    with tracer.start_span(SpanKind.KNOWLEDGE_SEARCH, "query") as sq:
                        sq.set_attribute("query", "API 限流 429 解决方案")
                        sq.set_attribute("scope", "knowledge")
                        sq.set_attribute("results_count", 3)
                        metrics.observe(LoomMetrics.KNOWLEDGE_RESULTS_COUNT, 3)
                        await asyncio.sleep(0.008)
                    metrics.observe(LoomMetrics.KNOWLEDGE_SEARCH_LATENCY,
                                    (time.monotonic() - t0) * 1000)

                    metrics.increment(LoomMetrics.TOOL_CALLS_TOTAL)

            metrics.set_gauge(LoomMetrics.CONTEXT_BUDGET_USED, 0.3 * i)

    # 输出结果
    summary = tracer.get_trace_summary()
    snap = metrics.snapshot()

    print("\n  Trace 摘要:")
    print(f"    spans: {summary['span_count']}")
    print(f"    duration: {summary['total_duration_ms']:.1f}ms")
    print(f"    by_kind: {summary['spans_by_kind']}")

    print("\n  Metrics 摘要:")
    c = snap["counters"]
    print(f"    迭代: {c.get(LoomMetrics.ITERATIONS_TOTAL, 0):.0f}")
    print(f"    工具调用: {c.get(LoomMetrics.TOOL_CALLS_TOTAL, 0):.0f}")
    print(f"    知识搜索: {c.get(LoomMetrics.KNOWLEDGE_SEARCH_TOTAL, 0):.0f}")
    print(f"    总输入 tokens: {c.get(LoomMetrics.TOKEN_INPUT, 0):.0f}")
    print(f"    总输出 tokens: {c.get(LoomMetrics.TOKEN_OUTPUT, 0):.0f}")

    h = snap["histograms"]
    llm_h = h.get(LoomMetrics.LLM_LATENCY, {})
    print(f"    LLM 平均延迟: {llm_h.get('avg', 0):.1f}ms")

    print(f"    预算使用率: {snap['gauges'].get(LoomMetrics.CONTEXT_BUDGET_USED, 0):.0%}")


async def main():
    print()
    print("Tracing 与 Metrics 可观测性 Demo")
    print()

    await demo_basic_tracing()
    await demo_error_tracing()
    await demo_metrics_counters()
    await demo_metrics_histograms()
    await demo_metrics_gauges()
    await demo_full_trace_simulation()

    print("\n" + "=" * 60)
    print("Demo 完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
