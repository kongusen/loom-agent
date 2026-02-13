"""
Tests for Unified Search Tool (query tool auto-wiring)

覆盖：
- _strip_importance_tag: importance 标记剥离
- UnifiedSearchToolBuilder: 工具定义动态生成
- UnifiedSearchExecutor: 统一检索执行
- KnowledgeAction: 事件类型枚举
- MEMORY_GUIDANCE: system prompt 注入
"""

import pytest

from loom.agent.core import MEMORY_GUIDANCE, _strip_importance_tag
from loom.context.retrieval.candidates import CandidateOrigin
from loom.events.actions import KnowledgeAction
from loom.tools.search.builder import UnifiedSearchToolBuilder

# ==================== _strip_importance_tag ====================


class TestStripImportanceTag:
    """importance 标记剥离"""

    def test_no_tag(self):
        text = "这是一个普通回复。"
        clean, imp = _strip_importance_tag(text)
        assert clean == text
        assert imp is None

    def test_tag_at_end(self):
        text = "建议使用 OAuth2.0。<imp:0.8/>"
        clean, imp = _strip_importance_tag(text)
        assert clean == "建议使用 OAuth2.0。"
        assert imp == 0.8

    def test_tag_with_trailing_whitespace(self):
        text = "重要结论。<imp:0.9/>  \n"
        clean, imp = _strip_importance_tag(text)
        assert clean == "重要结论。"
        assert imp == 0.9

    def test_tag_1_0(self):
        text = "极其重要<imp:1.0/>"
        clean, imp = _strip_importance_tag(text)
        assert clean == "极其重要"
        assert imp == 1.0

    def test_tag_0_0(self):
        text = "不重要<imp:0.0/>"
        clean, imp = _strip_importance_tag(text)
        assert clean == "不重要"
        assert imp == 0.0

    def test_tag_in_middle_ignored(self):
        """标记不在末尾时不匹配"""
        text = "前面<imp:0.5/>后面"
        clean, imp = _strip_importance_tag(text)
        assert clean == text
        assert imp is None

    def test_empty_string(self):
        clean, imp = _strip_importance_tag("")
        assert clean == ""
        assert imp is None

    def test_malformed_tag(self):
        text = "回复<imp:abc/>"
        clean, imp = _strip_importance_tag(text)
        assert clean == text
        assert imp is None

    def test_tag_value_precision(self):
        text = "回复<imp:0.75/>"
        clean, imp = _strip_importance_tag(text)
        assert clean == "回复"
        assert imp == 0.75


# ==================== CandidateOrigin.MEMORY ====================


class TestCandidateOriginMemory:
    """CandidateOrigin.MEMORY 枚举值"""

    def test_memory_exists(self):
        assert hasattr(CandidateOrigin, "MEMORY")
        assert CandidateOrigin.MEMORY.value == "memory"

    def test_all_origins(self):
        origins = {o.value for o in CandidateOrigin}
        assert "memory" in origins
        assert "l4_semantic" in origins
        assert "rag_knowledge" in origins


# ==================== KnowledgeAction ====================


class TestKnowledgeAction:
    """KnowledgeAction 事件类型"""

    def test_search_action(self):
        assert KnowledgeAction.SEARCH == "knowledge.search"

    def test_search_result_action(self):
        assert KnowledgeAction.SEARCH_RESULT == "knowledge.result"

    def test_is_str(self):
        assert isinstance(KnowledgeAction.SEARCH, str)


# ==================== UnifiedSearchToolBuilder ====================


class TestUnifiedSearchToolBuilder:
    """统一检索工具构建器"""

    def setup_method(self):
        self.builder = UnifiedSearchToolBuilder()

    def test_memory_only_tool(self):
        """无知识库时退化为纯记忆检索"""
        tool = self.builder.build_tool()
        func = tool["function"]

        assert func["name"] == "query"
        assert "query" in func["parameters"]["properties"]
        assert "layer" in func["parameters"]["properties"]
        assert "scope" not in func["parameters"]["properties"]
        assert func["parameters"]["required"] == ["query"]

    def test_memory_only_tool_layer_enum(self):
        tool = self.builder.build_tool()
        layer_prop = tool["function"]["parameters"]["properties"]["layer"]
        assert set(layer_prop["enum"]) == {"auto", "l1", "l2", "l3", "l4"}

    def test_unified_tool_with_knowledge(self):
        """有知识库时升级为统一检索工具"""
        kb = _MockKB("product_docs", "产品文档", ["产品功能", "API用法"])
        tool = self.builder.build_tool(knowledge_bases=[kb])
        func = tool["function"]

        assert func["name"] == "query"
        props = func["parameters"]["properties"]
        assert "query" in props
        assert "scope" in props
        assert "intent" in props
        # 单知识库不生成 source 参数
        assert "source" not in props

    def test_unified_tool_scope_enum(self):
        kb = _MockKB("docs", "文档")
        tool = self.builder.build_tool(knowledge_bases=[kb])
        scope_prop = tool["function"]["parameters"]["properties"]["scope"]
        assert set(scope_prop["enum"]) == {"auto", "memory", "knowledge", "all"}

    def test_multi_kb_adds_source_param(self):
        """多知识库时增加 source 参数"""
        kb1 = _MockKB("docs", "文档")
        kb2 = _MockKB("faq", "FAQ")
        tool = self.builder.build_tool(knowledge_bases=[kb1, kb2])
        props = tool["function"]["parameters"]["properties"]

        assert "source" in props
        assert set(props["source"]["enum"]) == {"docs", "faq"}

    def test_description_includes_kb_info(self):
        kb = _MockKB("product_docs", "产品文档和API参考")
        tool = self.builder.build_tool(knowledge_bases=[kb])
        desc = tool["function"]["description"]

        assert "product_docs" in desc
        assert "产品文档和API参考" in desc

    def test_description_includes_search_hints(self):
        kb = _MockKB("docs", "文档", search_hints=["产品功能", "配置参数"])
        tool = self.builder.build_tool(knowledge_bases=[kb])
        desc = tool["function"]["description"]

        assert "产品功能" in desc
        assert "配置参数" in desc

    def test_filters_from_kb(self):
        kb = _MockKB("docs", "文档", supported_filters=["category", "version"])
        tool = self.builder.build_tool(knowledge_bases=[kb])
        props = tool["function"]["parameters"]["properties"]

        assert "filters" in props
        assert "category" in props["filters"]["description"]
        assert "version" in props["filters"]["description"]

    def test_memory_disabled(self):
        kb = _MockKB("docs", "文档")
        tool = self.builder.build_tool(knowledge_bases=[kb], memory_enabled=False)
        desc = tool["function"]["description"]

        assert "搜索外部知识库" in desc
        assert "对话记忆" not in desc


# ==================== UnifiedSearchExecutor ====================


class TestUnifiedSearchExecutor:
    """统一检索执行器"""

    @pytest.mark.asyncio
    async def test_no_sources_returns_empty(self):
        from loom.tools.search.executor import UnifiedSearchExecutor

        executor = UnifiedSearchExecutor()
        result = await executor.execute("test query")
        assert "未找到" in result

    def test_resolve_scope_explicit(self):
        from loom.tools.search.executor import UnifiedSearchExecutor

        executor = UnifiedSearchExecutor()
        assert executor._resolve_scope("memory") == "memory"
        assert executor._resolve_scope("knowledge") == "knowledge"
        assert executor._resolve_scope("all") == "all"

    def test_resolve_scope_auto_no_kb(self):
        from loom.tools.search.executor import UnifiedSearchExecutor

        executor = UnifiedSearchExecutor()
        assert executor._resolve_scope("auto") == "memory"

    def test_resolve_scope_auto_with_kb(self):
        from loom.tools.search.executor import UnifiedSearchExecutor

        kb = _MockKB("docs", "文档")
        executor = UnifiedSearchExecutor(knowledge_bases=[kb])
        assert executor._resolve_scope("auto") == "all"

    def test_text_match_basic(self):
        from loom.tools.search.executor import UnifiedSearchExecutor

        assert UnifiedSearchExecutor._text_match("hello world", "Hello World Test")
        assert UnifiedSearchExecutor._text_match("python", "Learning Python Programming")
        assert not UnifiedSearchExecutor._text_match("javascript", "Learning Python Programming")

    def test_text_match_empty_query(self):
        from loom.tools.search.executor import UnifiedSearchExecutor

        assert UnifiedSearchExecutor._text_match("", "any content")

    def test_text_match_short_words_ignored(self):
        from loom.tools.search.executor import UnifiedSearchExecutor

        # Single-char words are filtered out
        assert UnifiedSearchExecutor._text_match("a", "any content")


# ==================== MEMORY_GUIDANCE ====================


class TestMemoryGuidance:
    """MEMORY_GUIDANCE system prompt 内容"""

    def test_contains_search_guidance(self):
        assert "query" in MEMORY_GUIDANCE
        assert "scope" in MEMORY_GUIDANCE

    def test_contains_importance_guidance(self):
        assert "<imp:" in MEMORY_GUIDANCE
        assert "importance" in MEMORY_GUIDANCE.lower()

    def test_contains_scope_options(self):
        assert "auto" in MEMORY_GUIDANCE
        assert "memory" in MEMORY_GUIDANCE
        assert "knowledge" in MEMORY_GUIDANCE


# ==================== promote_task_to_l2 (removed in 3-layer architecture) ====================


# TestPromoteTaskToL2 has been removed — the old importance_threshold,
# add_task, promote_task_to_l2 APIs no longer exist in the 3-layer
# LoomMemory architecture. L1→L2 promotion is now automatic via
# eviction callbacks.


# ==================== KnowledgeAction in query routing ====================


class TestKnowledgeActionRouting:
    """EventBus 集成：query 路由创建 KnowledgeAction Task"""

    def test_search_task_fields(self):
        """验证 SearchTask 的字段结构"""
        from loom.runtime import Task

        task = Task(
            taskId="test-search-1",
            sourceAgent="agent-1",
            action=KnowledgeAction.SEARCH,
            parameters={"query": "API认证", "scope": "auto"},
            sessionId="session-1",
        )
        assert task.action == "knowledge.search"
        assert task.parameters["query"] == "API认证"
        assert task.sessionId == "session-1"

    def test_result_task_fields(self):
        """验证 ResultTask 的字段结构"""
        from loom.runtime import Task, TaskStatus

        task = Task(
            taskId="test-result-1",
            sourceAgent="agent-1",
            action=KnowledgeAction.SEARCH_RESULT,
            parameters={"query": "API认证", "scope": "auto"},
            result={"formatted_output": "搜索结果..."},
            status=TaskStatus.COMPLETED,
            sessionId="session-1",
            parentTaskId="test-search-1",
        )
        assert task.action == "knowledge.result"
        assert task.status == TaskStatus.COMPLETED
        assert task.result["formatted_output"] == "搜索结果..."
        assert task.parentTaskId == "test-search-1"


# ==================== Helpers ====================


class _MockKB:
    """Mock KnowledgeBaseProvider for testing"""

    def __init__(
        self,
        name: str = "mock_kb",
        description: str = "",
        search_hints: list[str] | None = None,
        supported_filters: list[str] | None = None,
    ):
        self._name = name
        self._description = description
        self._search_hints = search_hints or []
        self._supported_filters = supported_filters or []

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def search_hints(self) -> list[str]:
        return self._search_hints

    @property
    def supported_filters(self) -> list[str]:
        return self._supported_filters

    async def query(self, **kwargs):
        return []

    async def get_by_id(self, item_id: str):
        return None


# ==================== _query_similar ====================


class TestQuerySimilar:
    """查询相似度判断"""

    def test_identical_queries(self):
        from loom.tools.search.executor import UnifiedSearchExecutor

        assert UnifiedSearchExecutor._query_similar("API认证", "API认证")

    def test_subset_query(self):
        from loom.tools.search.executor import UnifiedSearchExecutor

        assert UnifiedSearchExecutor._query_similar("API认证", "API认证 方案")

    def test_superset_query(self):
        from loom.tools.search.executor import UnifiedSearchExecutor

        assert UnifiedSearchExecutor._query_similar("API认证 方案 推荐", "API认证")

    def test_high_jaccard(self):
        from loom.tools.search.executor import UnifiedSearchExecutor

        # 3/4 overlap = 0.75 >= 0.6
        assert UnifiedSearchExecutor._query_similar(
            "python async await patterns",
            "python async await examples",
        )

    def test_low_jaccard(self):
        from loom.tools.search.executor import UnifiedSearchExecutor

        # completely different
        assert not UnifiedSearchExecutor._query_similar(
            "python programming",
            "javascript framework",
        )

    def test_empty_query(self):
        from loom.tools.search.executor import UnifiedSearchExecutor

        assert not UnifiedSearchExecutor._query_similar("", "API认证")
        assert not UnifiedSearchExecutor._query_similar("API认证", "")

    def test_short_words_fallback_to_exact(self):
        from loom.tools.search.executor import UnifiedSearchExecutor

        # all words < 2 chars → fallback to exact match
        assert UnifiedSearchExecutor._query_similar("a", "a")
        assert not UnifiedSearchExecutor._query_similar("a", "b")

    def test_case_insensitive(self):
        from loom.tools.search.executor import UnifiedSearchExecutor

        assert UnifiedSearchExecutor._query_similar("Hello World", "hello world")


# TestCheckL1Cache removed — _check_l1_cache was removed in the 3-layer
# architecture. L1 stores messages, not search result tasks.
