"""
17_memory_rag_autowiring.py - Memory + RAG + Knowledge 自动接线

演示：
- KnowledgeBaseProvider 元信息声明（name/description/search_hints/supported_filters）
- UnifiedSearchToolBuilder 动态工具生成（零配置 vs 多知识库）
- UnifiedSearchExecutor 统一检索执行（记忆 + 知识库）
- Agent.create 传入 knowledge_base 自动获得搜索能力
- Importance 标记机制（<imp:X.X/>）
- Observability 集成（LoomTracer / LoomMetrics）

设计文档：docs/design/memory-rag-knowledge-tool-autowiring.md
"""

import asyncio
from typing import Any

from loom.agent.core import _strip_importance_tag
from loom.observability import LoomMetrics, LoomTracer, SpanKind
from loom.providers.knowledge.base import KnowledgeBaseProvider, KnowledgeItem
from loom.tools.search.builder import UnifiedSearchToolBuilder
from loom.tools.search.executor import UnifiedSearchExecutor

# ============================================================
# 1. 自定义 KnowledgeBaseProvider（声明元信息）
# ============================================================


class ProductDocsKB(KnowledgeBaseProvider):
    """产品文档知识库 — 演示元信息声明"""

    _docs = [
        KnowledgeItem(
            id="doc-auth",
            content="OAuth2.0 支持 Authorization Code 和 Client Credentials 两种模式。"
            "Web 应用推荐 Authorization Code，服务间调用推荐 Client Credentials。",
            source="product_docs",
            relevance=0.0,
            metadata={"category": "auth", "version": "2.0"},
        ),
        KnowledgeItem(
            id="doc-rate-limit",
            content="API 限流策略：免费用户 100 次/分钟，付费用户 1000 次/分钟。"
            "超限返回 HTTP 429，建议使用指数退避重试。",
            source="product_docs",
            relevance=0.0,
            metadata={"category": "api", "version": "2.0"},
        ),
        KnowledgeItem(
            id="doc-webhook",
            content="Webhook 回调支持 HMAC-SHA256 签名验证。"
            "配置时需提供 callback URL 和 secret，系统会在事件触发时 POST 通知。",
            source="product_docs",
            relevance=0.0,
            metadata={"category": "webhook", "version": "2.0"},
        ),
    ]

    @property
    def name(self) -> str:
        return "product_docs"

    @property
    def description(self) -> str:
        return "产品文档和 API 参考手册"

    @property
    def search_hints(self) -> list[str]:
        return ["产品功能", "API 用法", "错误排查"]

    @property
    def supported_filters(self) -> list[str]:
        return ["category", "version"]

    async def query(
        self,
        query: str,
        limit: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[KnowledgeItem]:
        """简单关键词匹配（演示用）"""
        results = []
        q = query.lower()
        for doc in self._docs:
            score = sum(1 for w in q.split() if w in doc.content.lower()) / max(len(q.split()), 1)
            if score > 0 or not q.strip():
                results.append(
                    KnowledgeItem(
                        id=doc.id,
                        content=doc.content,
                        source=doc.source,
                        relevance=min(score * 1.5, 1.0),
                        metadata=doc.metadata,
                    )
                )
        # 过滤
        if filters:
            for key, val in filters.items():
                results = [r for r in results if r.metadata.get(key) == val]
        results.sort(key=lambda r: r.relevance, reverse=True)
        return results[:limit]

    async def get_by_id(self, knowledge_id: str) -> KnowledgeItem | None:
        return next((d for d in self._docs if d.id == knowledge_id), None)


class FAQKB(KnowledgeBaseProvider):
    """常见问题知识库"""

    _faqs = [
        KnowledgeItem(
            id="faq-reset-pwd",
            content="重置密码：进入设置 > 安全 > 修改密码，输入旧密码和新密码即可。",
            source="faq",
            relevance=0.0,
            metadata={"topic": "account"},
        ),
        KnowledgeItem(
            id="faq-billing",
            content="账单周期为自然月，每月 1 日扣费。可在账单页面查看历史账单和下载发票。",
            source="faq",
            relevance=0.0,
            metadata={"topic": "billing"},
        ),
    ]

    @property
    def name(self) -> str:
        return "faq"

    @property
    def description(self) -> str:
        return "常见问题与解答"

    @property
    def search_hints(self) -> list[str]:
        return ["账户问题", "计费", "常见错误"]

    @property
    def supported_filters(self) -> list[str]:
        return ["topic"]

    async def query(
        self,
        query: str,
        limit: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[KnowledgeItem]:
        results = []
        q = query.lower()
        for faq in self._faqs:
            score = sum(1 for w in q.split() if w in faq.content.lower()) / max(len(q.split()), 1)
            if score > 0:
                results.append(
                    KnowledgeItem(
                        id=faq.id,
                        content=faq.content,
                        source=faq.source,
                        relevance=min(score * 1.5, 1.0),
                        metadata=faq.metadata,
                    )
                )
        results.sort(key=lambda r: r.relevance, reverse=True)
        return results[:limit]

    async def get_by_id(self, knowledge_id: str) -> KnowledgeItem | None:
        return next((f for f in self._faqs if f.id == knowledge_id), None)


# ============================================================
# Demo 函数
# ============================================================


async def demo_tool_builder():
    """演示 UnifiedSearchToolBuilder 动态工具生成"""
    print("=" * 60)
    print("[1] UnifiedSearchToolBuilder — 动态工具生成")
    print("=" * 60)

    builder = UnifiedSearchToolBuilder()
    product_kb = ProductDocsKB()
    faq_kb = FAQKB()

    # --- 场景 A: 无知识库 → 纯记忆检索工具 ---
    tool_memory_only = builder.build_tool(knowledge_bases=None, memory_enabled=True)
    func = tool_memory_only["function"]
    print("\n  [A] 无知识库（纯记忆检索）")
    print(f"      工具名: {func['name']}")
    print(f"      描述: {func['description'][:60]}...")
    print(f"      参数: {list(func['parameters']['properties'].keys())}")

    # --- 场景 B: 单知识库 → 统一检索（无 source 参数）---
    tool_single = builder.build_tool(knowledge_bases=[product_kb], memory_enabled=True)
    func = tool_single["function"]
    print("\n  [B] 单知识库（统一检索）")
    print(f"      工具名: {func['name']}")
    print(f"      描述: {func['description'][:80]}...")
    params = list(func["parameters"]["properties"].keys())
    print(f"      参数: {params}")
    print(f"      有 source 参数: {'source' in params}")

    # --- 场景 C: 多知识库 → 统一检索（含 source 参数）---
    tool_multi = builder.build_tool(knowledge_bases=[product_kb, faq_kb], memory_enabled=True)
    func = tool_multi["function"]
    print("\n  [C] 多知识库（统一检索 + source 选择）")
    print(f"      工具名: {func['name']}")
    print(f"      描述: {func['description'][:80]}...")
    params = list(func["parameters"]["properties"].keys())
    print(f"      参数: {params}")
    if "source" in func["parameters"]["properties"]:
        sources = func["parameters"]["properties"]["source"]["enum"]
        print(f"      可选知识源: {sources}")
    if "filters" in func["parameters"]["properties"]:
        print(f"      过滤条件: {func['parameters']['properties']['filters']['description']}")


async def demo_search_executor():
    """演示 UnifiedSearchExecutor 统一检索"""
    print("\n" + "=" * 60)
    print("[2] UnifiedSearchExecutor — 统一检索执行")
    print("=" * 60)

    product_kb = ProductDocsKB()
    faq_kb = FAQKB()

    executor = UnifiedSearchExecutor(
        memory=None,  # 无记忆（纯知识库演示）
        knowledge_bases=[product_kb, faq_kb],
        default_limit=3,
        min_relevance=0.1,
    )

    # --- 搜索 1: scope=auto（自动路由到全部源）---
    print("\n  [搜索 1] scope=auto, query='OAuth2.0 认证模式'")
    result = await executor.execute(query="OAuth2.0 认证模式", scope="auto")
    for line in result.strip().split("\n")[:6]:
        print(f"    {line}")

    # --- 搜索 2: scope=knowledge, source=faq ---
    print("\n  [搜索 2] scope=knowledge, source='faq', query='密码'")
    result = await executor.execute(query="密码", scope="knowledge", source="faq")
    for line in result.strip().split("\n")[:6]:
        print(f"    {line}")

    # --- 搜索 3: 带 intent 的搜索 ---
    print("\n  [搜索 3] intent='troubleshooting', query='API 限流 429'")
    result = await executor.execute(query="API 限流 429", intent="troubleshooting")
    for line in result.strip().split("\n")[:6]:
        print(f"    {line}")


async def demo_importance_tag():
    """演示 Importance 标记机制"""
    print("\n" + "=" * 60)
    print("[3] Importance 标记 — <imp:X.X/> 剥离与提升")
    print("=" * 60)

    test_cases = [
        ("普通回复，没有标记。", None),
        ("建议使用 Authorization Code 模式。<imp:0.8/>", 0.8),
        ("这是关键架构决策，必须记住。<imp:0.9/>", 0.9),
        ("闲聊内容，不需要记忆。", None),
    ]

    for raw, expected_imp in test_cases:
        clean, importance = _strip_importance_tag(raw)
        tag = f"imp={importance}" if importance else "无标记"
        action = ""
        if importance and importance > 0.6:
            action = " → 立即提升到 L2"
        elif importance:
            action = " → 留在 L1"
        print(f'\n  原始: "{raw}"')
        print(f'  清理: "{clean}"')
        print(f"  结果: {tag}{action}")
        assert importance == expected_imp, f"Expected {expected_imp}, got {importance}"

    print("\n  所有断言通过")


async def demo_observability():
    """演示 Observability 集成"""
    print("\n" + "=" * 60)
    print("[4] Observability — LoomTracer + LoomMetrics")
    print("=" * 60)

    # --- LoomTracer ---
    LoomTracer()
    print("\n  LoomTracer 已创建")

    # 演示 SpanKind 中的知识搜索类型
    print(f"  SpanKind.KNOWLEDGE_SEARCH = {SpanKind.KNOWLEDGE_SEARCH.value}")
    print(f"  SpanKind.KNOWLEDGE_RETRIEVAL = {SpanKind.KNOWLEDGE_RETRIEVAL.value}")

    # --- LoomMetrics ---
    metrics = LoomMetrics()
    print("\n  LoomMetrics 已创建")

    # 模拟知识搜索指标
    metrics.increment(LoomMetrics.KNOWLEDGE_SEARCH_TOTAL)
    metrics.increment(LoomMetrics.KNOWLEDGE_SEARCH_TOTAL)
    metrics.observe(LoomMetrics.KNOWLEDGE_SEARCH_LATENCY, 45.2)
    metrics.observe(LoomMetrics.KNOWLEDGE_SEARCH_LATENCY, 32.1)
    metrics.observe(LoomMetrics.KNOWLEDGE_RESULTS_COUNT, 3)

    snapshot = metrics.snapshot()
    print(f"  搜索次数: {snapshot['counters'].get(LoomMetrics.KNOWLEDGE_SEARCH_TOTAL, 0)}")
    latency = snapshot["histograms"].get(LoomMetrics.KNOWLEDGE_SEARCH_LATENCY, {})
    print(f"  搜索延迟: avg={latency.get('avg', 0):.1f}ms, count={latency.get('count', 0)}")
    results = snapshot["histograms"].get(LoomMetrics.KNOWLEDGE_RESULTS_COUNT, {})
    print(f"  结果数量: avg={results.get('avg', 0):.1f}, count={results.get('count', 0)}")


async def demo_agent_autowiring():
    """演示 Agent.create 自动接线（不需要 LLM，仅展示工具生成）"""
    print("\n" + "=" * 60)
    print("[5] Agent.create 自动接线 — 传入 knowledge_base 即获得搜索能力")
    print("=" * 60)

    # 这里不实际调用 LLM，仅展示 Agent 构建后的工具列表
    # 需要一个 LLM provider，使用 mock
    from unittest.mock import AsyncMock, MagicMock

    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value={"content": "mock"})
    mock_llm.model = "mock-model"
    mock_llm.supports_streaming = False

    from loom.agent import Agent

    product_kb = ProductDocsKB()
    faq_kb = FAQKB()

    # --- 场景 A: 无知识库 ---
    agent_no_kb = Agent.create(
        llm=mock_llm,
        system_prompt="你是一个助手。",
        max_iterations=1,
    )
    query_tools_a = [
        t for t in agent_no_kb.all_tools if t.get("function", {}).get("name") == "query"
    ]
    print("\n  [A] 无知识库")
    print(f"      query 工具数: {len(query_tools_a)}")
    if query_tools_a:
        params = list(query_tools_a[0]["function"]["parameters"]["properties"].keys())
        print(f"      参数: {params}")

    # --- 场景 B: 单知识库 ---
    agent_single = Agent.create(
        llm=mock_llm,
        system_prompt="你是一个产品助手。",
        knowledge_base=product_kb,
        max_iterations=1,
    )
    query_tools_b = [
        t for t in agent_single.all_tools if t.get("function", {}).get("name") == "query"
    ]
    print("\n  [B] 单知识库 (product_docs)")
    print(f"      query 工具数: {len(query_tools_b)}")
    if query_tools_b:
        func = query_tools_b[0]["function"]
        params = list(func["parameters"]["properties"].keys())
        print(f"      参数: {params}")
        print(f"      描述片段: {func['description'][:60]}...")

    # --- 场景 C: 多知识库 ---
    agent_multi = Agent.create(
        llm=mock_llm,
        system_prompt="你是一个全栈助手。",
        knowledge_base=[product_kb, faq_kb],
        max_iterations=1,
    )
    query_tools_c = [
        t for t in agent_multi.all_tools if t.get("function", {}).get("name") == "query"
    ]
    print("\n  [C] 多知识库 (product_docs + faq)")
    print(f"      query 工具数: {len(query_tools_c)}")
    if query_tools_c:
        func = query_tools_c[0]["function"]
        params = list(func["parameters"]["properties"].keys())
        print(f"      参数: {params}")
        if "source" in func["parameters"]["properties"]:
            sources = func["parameters"]["properties"]["source"]["enum"]
            print(f"      可选知识源: {sources}")

    # 验证 system prompt 包含 MEMORY_GUIDANCE
    has_guidance = "<memory_management>" in agent_single.system_prompt
    print(f"\n  System prompt 包含 MEMORY_GUIDANCE: {has_guidance}")


async def main():
    print()
    print("Memory + RAG + Knowledge Tool Auto-Wiring Demo")
    print("设计文档: docs/design/memory-rag-knowledge-tool-autowiring.md")
    print()

    await demo_tool_builder()
    await demo_search_executor()
    await demo_importance_tag()
    await demo_observability()
    await demo_agent_autowiring()

    print("\n" + "=" * 60)
    print("Demo 完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
